import csv
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Optional, Set, Tuple, List

from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait

from review_analysis.crawling.base_crawler import BaseCrawler
from utils.logger import setup_logger


@dataclass(frozen=True)
class ReviewRow:
    """One review row in the required output schema."""
    rating: str
    date: str
    content: str


class AladinCrawler(BaseCrawler):
    """
    Aladin 100자평(전체) crawler.

    Target flow:
    - 상품 페이지 접속
    - 100자평 탭에서 '전체' 선택
    - '더보기' 반복 호출로 리뷰 로딩
    - 각 카드(div.hundred_list)에서 (rating, date, content) 추출
    - PaperId 기준 중복 제거
    """

    TARGET_URL = "https://www.aladin.co.kr/shop/wproduct.aspx?ItemId=40869703"
    TARGET_COUNT = 550  # 테스트 시 20 등으로 변경

    def __init__(self, output_dir: str):
        super().__init__(output_dir)
        self.logger = setup_logger()
        self.driver: Optional[WebDriver] = None

        self.rows: List[ReviewRow] = []
        self.seen_ids: Set[str] = set()

        self._silence_problematic_logs()

    def _silence_problematic_logs(self) -> None:
        """Reduce noisy selenium/urllib3 logs that can trigger encoding issues on some Windows consoles."""
        for name in [
            "selenium",
            "selenium.webdriver",
            "selenium.webdriver.remote",
            "selenium.webdriver.remote.remote_connection",
            "urllib3",
            "urllib3.connectionpool",
        ]:
            logging.getLogger(name).setLevel(logging.CRITICAL)

    def start_browser(self) -> None:
        """Start headless Chrome."""
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--window-size=1400,900")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--lang=ko-KR")
        chrome_options.page_load_strategy = "eager"

        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.set_page_load_timeout(45)
        self.logger.info("Chrome started (headless).")

    def scrape_reviews(self) -> None:
        """
        Crawl reviews into self.rows.
        Ensures the review area is visible (lazy-load scroll), switches to 전체 tab,
        and repeatedly clicks 더보기 until TARGET_COUNT is reached or no more progress.
        """
        if self.driver is None:
            self.start_browser()

        assert self.driver is not None
        driver = self.driver

        wait = WebDriverWait(driver, 15)
        more_wait = WebDriverWait(driver, 30)

        driver.get(self.TARGET_URL)

        self._scroll_until_review_area_visible()
        self._click_total_tab()

        # "전체" 전환 후 카드가 생성되도록 잠깐 대기(없어도 진행은 함)
        try:
            wait.until(lambda d: len(self._find_review_cards()) > 0)
        except TimeoutException:
            self.logger.warning("No review cards visible after switching to '전체' tab (continuing).")

        stagnation = 0
        last_count = 0

        while len(self.rows) < self.TARGET_COUNT:
            cards = self._find_review_cards()
            self._extract_from_cards(cards)
            self.logger.info(f"Collected so far: {len(self.rows)}")

            if len(self.rows) == last_count:
                stagnation += 1
                self.logger.warning(f"No new reviews collected (stagnation={stagnation}).")
            else:
                stagnation = 0
                last_count = len(self.rows)

            if len(self.rows) >= self.TARGET_COUNT:
                break

            ok = self._click_more_and_wait(more_wait)
            if not ok:
                self.logger.warning("Stop: failed to load more reviews (no change detected).")
                break

            time.sleep(0.4)

            if stagnation >= 10:
                self.logger.error("Stuck collecting reviews: count not increasing despite attempts.")
                break

        self.logger.info(f"Scrape finished: {len(self.rows)} reviews collected.")

        try:
            driver.quit()
        except Exception:
            pass
        self.logger.info("Browser closed.")

    def save_to_database(self) -> None:
        """Save self.rows to CSV (required schema)."""
        os.makedirs(self.output_dir, exist_ok=True)
        out_path = os.path.join(self.output_dir, "reviews_aladin.csv")

        # Excel 호환까지 고려: utf-8-sig
        with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["rating", "date", "content"])
            for r in self.rows:
                w.writerow([r.rating, r.date, r.content])

        self.logger.info(f"Saved CSV: {out_path} (rows={len(self.rows)})")

    # -----------------------------
    # DOM helpers
    # -----------------------------

    def _scroll_until_review_area_visible(self) -> None:
        """
        Aladin 페이지는 100자평 DOM이 스크롤 후 생성되는 경우가 있음.
        아래 요소 중 하나라도 보일 때까지 스크롤:
        - #tabTotal
        - div.hundred_list
        - 더보기 버튼 (fn_CommunityReviewMore)
        """
        assert self.driver is not None
        driver = self.driver

        for _ in range(50):
            if driver.find_elements(By.CSS_SELECTOR, "#tabTotal"):
                return
            if driver.find_elements(By.CSS_SELECTOR, "div.hundred_list"):
                return
            if driver.find_elements(By.CSS_SELECTOR, "div.Ere_btn_more a[href*='fn_CommunityReviewMore']"):
                return

            driver.execute_script("window.scrollBy(0, 900);")
            time.sleep(0.25)

        self.logger.warning("Could not find review area elements after scrolling.")

    def _click_total_tab(self) -> None:
        """
        100자평 -> 전체 탭 전환.
        1) #tabTotal 클릭
        2) onclick 패턴(fn_IsOrdererCommentReview, 2, ...) 후보 클릭
        3) JS 직접 호출(가능하면)
        """
        assert self.driver is not None
        driver = self.driver

        # 1) Click by id
        try:
            el = driver.find_element(By.CSS_SELECTOR, "#tabTotal")
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            time.sleep(0.15)
            driver.execute_script("arguments[0].click();", el)
            time.sleep(0.6)
            return
        except Exception:
            pass

        # 2) Click by onclick regex (robust to spacing)
        try:
            driver.execute_script(r"""
                try {
                  const links = Array.from(document.querySelectorAll("a[onclick*='fn_IsOrdererCommentReview']"));
                  const re = /,\s*2\s*,/; // 전체 탭: 2
                  const cand = links.find(a => re.test(a.getAttribute('onclick') || ''));
                  if (cand) cand.click();
                } catch(e) {}
            """)
            time.sleep(0.6)
            return
        except Exception:
            pass

        # 3) Direct JS call (works only if tabTotal exists)
        try:
            driver.execute_script(
                "try { fn_IsOrdererCommentReview(document.getElementById('tabTotal'), 2, 'commentreview_sort_Isorderer'); } catch(e) {}"
            )
            time.sleep(0.6)
        except Exception:
            pass

    def _find_review_cards(self) -> List[WebElement]:
        """Return review cards (div.hundred_list)."""
        assert self.driver is not None
        return self.driver.find_elements(By.CSS_SELECTOR, "div.hundred_list")

    def _click_more_and_wait(self, wait: WebDriverWait) -> bool:
        """
        Click '더보기' and wait for change.
        Success if:
        - card count increases OR
        - visible PaperId set changes (re-render/replace case)
        """
        assert self.driver is not None
        driver = self.driver

        before_cards = self._find_review_cards()
        before_n = len(before_cards)
        before_ids = self._visible_paper_ids(before_cards)

        # JS first
        try:
            driver.execute_script("try { fn_CommunityReviewMore(); } catch(e) {}")
        except Exception:
            pass

        # Button fallback
        try:
            more_a = driver.find_element(By.CSS_SELECTOR, "div.Ere_btn_more a[href*='fn_CommunityReviewMore']")
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", more_a)
            time.sleep(0.2)
            driver.execute_script("arguments[0].click();", more_a)
        except NoSuchElementException:
            pass
        except Exception:
            pass

        def changed(_: WebDriver) -> bool:
            cards = self._find_review_cards()
            if len(cards) > before_n:
                return True
            cur_ids = self._visible_paper_ids(cards)
            return len(cur_ids - before_ids) > 0

        try:
            wait.until(changed)
            return True
        except TimeoutException:
            return False

    def _visible_paper_ids(self, cards: List[WebElement]) -> Set[str]:
        """Collect PaperIds from given cards (best-effort)."""
        ids: Set[str] = set()
        for c in cards:
            try:
                rid = self._extract_paper_id(c)
                if rid:
                    ids.add(rid)
            except Exception:
                continue
        return ids

    def _extract_from_cards(self, cards: List[WebElement]) -> int:
        """Extract ReviewRow from cards, append to self.rows (dedup by PaperId)."""
        added = 0
        for card in cards:
            if len(self.rows) >= self.TARGET_COUNT:
                break

            try:
                row, rid = self._parse_one_card(card)
                if not rid:
                    continue
                if rid in self.seen_ids:
                    continue

                # content가 비면 '리뷰 내용' 요건을 엄밀히 만족하지 못하므로 제외
                if not row.content:
                    continue

                self.seen_ids.add(rid)
                self.rows.append(row)
                added += 1

            except StaleElementReferenceException:
                continue
            except Exception:
                continue

        return added

    def _parse_one_card(self, card: WebElement) -> Tuple[ReviewRow, str]:
        """Parse a single review card into (ReviewRow, PaperId)."""
        rid = self._extract_paper_id(card)
        rating = self._extract_rating(card)
        date = self._extract_date(card)
        content = self._extract_content(card)

        date = date.replace("\xa0", " ").strip()
        content = content.replace("\xa0", " ").strip()

        return ReviewRow(rating=rating, date=date, content=content), rid

    def _extract_paper_id(self, card: WebElement) -> str:
        """
        Extract PaperId.
        Priority:
        1) onclick="fn_ToggleCommentReviewPaper('ID')"
        2) span id="spnPaperID"
        3) div id="div_commentReviewPaperID"
        """
        # 1) onclick
        try:
            el = card.find_element(By.XPATH, ".//*[@onclick and contains(@onclick,'fn_ToggleCommentReviewPaper')]")
            onclick = el.get_attribute("onclick") or ""
            m = re.search(r"fn_ToggleCommentReviewPaper\('(\d+)'\)", onclick)
            if m:
                return m.group(1)
        except Exception:
            pass

        # 2) span id
        try:
            spans = card.find_elements(By.CSS_SELECTOR, "span[id^='spnPaper']")
            for sp in spans:
                sid = sp.get_attribute("id") or ""
                m = re.fullmatch(r"spnPaper(\d+)", sid)
                if m:
                    return m.group(1)
        except Exception:
            pass

        # 3) div id
        try:
            divs = card.find_elements(By.CSS_SELECTOR, "div[id^='div_commentReviewPaper']")
            for dv in divs:
                did = dv.get_attribute("id") or ""
                m = re.search(r"div_commentReviewPaper(\d+)", did)
                if m:
                    return m.group(1)
        except Exception:
            pass

        return ""

    def _extract_rating(self, card: WebElement) -> str:
        """Count filled stars (icon_star_on)."""
        try:
            imgs = card.find_elements(By.CSS_SELECTOR, ".HL_star img")
            on = 0
            for im in imgs:
                src = (im.get_attribute("src") or "").lower()
                if "icon_star_on" in src:
                    on += 1
            return str(on)
        except Exception:
            return ""

    def _extract_date(self, card: WebElement) -> str:
        """Extract YYYY-MM-DD date."""
        try:
            spans = card.find_elements(By.CSS_SELECTOR, ".left span")
            for sp in spans:
                t = (sp.text or "").strip()
                if re.fullmatch(r"\d{4}-\d{2}-\d{2}", t):
                    return t
        except Exception:
            pass

        try:
            txt = card.text or ""
            m = re.search(r"(\d{4}-\d{2}-\d{2})", txt)
            if m:
                return m.group(1)
        except Exception:
            pass

        return ""

    def _extract_content(self, card: WebElement) -> str:
        """
        Extract content from span with id exactly 'spnPaper{digits}'.
        Use textContent (not .text) to avoid empty strings in some render states.
        """
        assert self.driver is not None

        # 1) direct read
        try:
            spans = card.find_elements(By.CSS_SELECTOR, "span[id^='spnPaper']")
            for sp in spans:
                sid = sp.get_attribute("id") or ""
                if re.fullmatch(r"spnPaper\d+", sid):
                    t = (sp.get_attribute("textContent") or "").strip()
                    if t:
                        return t
        except Exception:
            pass

        # 2) click toggle once then retry (some cards populate on click)
        try:
            toggle = card.find_element(By.XPATH, ".//*[@onclick and contains(@onclick,'fn_ToggleCommentReviewPaper')]")
            try:
                self.driver.execute_script("arguments[0].click();", toggle)
                time.sleep(0.25)
            except Exception:
                pass

            spans = card.find_elements(By.CSS_SELECTOR, "span[id^='spnPaper']")
            for sp in spans:
                sid = sp.get_attribute("id") or ""
                if re.fullmatch(r"spnPaper\d+", sid):
                    t = (sp.get_attribute("textContent") or "").strip()
                    if t:
                        return t
        except Exception:
            pass

        return ""
