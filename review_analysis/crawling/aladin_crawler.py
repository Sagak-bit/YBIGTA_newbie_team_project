# review_analysis/crawling/aladin_crawler.py

import csv
import hashlib
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import List, Optional, Set, Tuple

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
    rating: str
    date: str
    content: str


class AladinCrawler(BaseCrawler):
    """
    Aladin crawler (100자평 전체 -> 필요 시 마이리뷰 전체로 fallback하여 최대 수집 시도)

    Flow:
    - 상품 페이지 접속
    - 100자평: 전체 탭 시도 -> 더보기 반복 -> 카드 파싱
    - 진행이 멈추면(더보기 타임아웃/증가 없음) 페이지를 새로고침하고
      마이리뷰: 전체 탭(#tabMyReviewTotal)으로 전환 -> 더보기 반복 -> 카드 파싱
    - 중복 제거: PaperId 우선, 없으면 (date|rating|content) md5 signature
    """

    TARGET_URL = "https://www.aladin.co.kr/shop/wproduct.aspx?ItemId=40869703"
    TARGET_COUNT = 550  # 최대 목표. 실제 노출/로딩 가능량이 더 적으면 그 이하로 종료될 수 있음.

    # wait tuning
    PAGELOAD_TIMEOUT = 90
    SCRIPT_TIMEOUT = 90
    WAIT_MAIN = 40
    WAIT_MORE = 180  # 더보기 로딩이 느릴 때 대비

    # retry tuning
    MORE_MAX_ATTEMPTS = 8
    STAGNATION_LIMIT = 10

    def __init__(self, output_dir: str):
        super().__init__(output_dir)
        self.logger = setup_logger()
        # __init__ 안에 추가 (setup_logger() 다음 줄에)
        self._ensure_console_logging(level=logging.INFO)

        self.driver: Optional[WebDriver] = None

        self.rows: List[ReviewRow] = []
        self.seen_ids: Set[str] = set()

        self._silence_problematic_logs()

    def _ensure_console_logging(self, level: int = logging.INFO) -> None:
        """
        setup_logger() 설정과 무관하게, 콘솔로 로그가 반드시 보이도록 보정.
        (중복 핸들러는 추가하지 않음)
        """
        logger = self.logger
        logger.setLevel(level)

        # 이미 StreamHandler가 있으면 그대로 사용
        for h in logger.handlers:
            if isinstance(h, logging.StreamHandler):
                h.setLevel(level)
                return

        sh = logging.StreamHandler()
        sh.setLevel(level)
        fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        sh.setFormatter(fmt)
        logger.addHandler(sh)

    # -----------------------------
    # Browser
    # -----------------------------
    def _silence_problematic_logs(self) -> None:
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
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--window-size=1400,900")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--lang=ko-KR")
        chrome_options.page_load_strategy = "eager"

        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.set_page_load_timeout(self.PAGELOAD_TIMEOUT)
        self.driver.set_script_timeout(self.SCRIPT_TIMEOUT)

    # -----------------------------
    # Public API
    # -----------------------------
    def scrape_reviews(self) -> None:
        if self.driver is None:
            self.start_browser()

        assert self.driver is not None
        driver = self.driver

        wait = WebDriverWait(driver, self.WAIT_MAIN)
        more_wait = WebDriverWait(driver, self.WAIT_MORE)

        driver.get(self.TARGET_URL)
        self._wait_ready_state(wait)

        # 1) 100자평 전체 시도
        self._scroll_until_review_area_visible(max_scrolls=100)
        self._click_hundred_total_tab()
        self._collect_loop(mode="hundred", wait=wait, more_wait=more_wait)

        # 2) 목표 미달이면: 새로고침 + 마이리뷰 전체로 fallback
        if len(self.rows) < self.TARGET_COUNT:
            try:
                driver.refresh()
                self._wait_ready_state(wait)
            except Exception:
                pass

            self._scroll_until_review_area_visible(max_scrolls=120)
            self._click_myreview_total_tab()
            self._collect_loop(mode="myreview", wait=wait, more_wait=more_wait)

        try:
            driver.quit()
        except Exception:
            pass

    def save_to_database(self) -> None:
        os.makedirs(self.output_dir, exist_ok=True)
        out_path = os.path.join(self.output_dir, "reviews_aladin.csv")

        with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["rating", "date", "content"])
            for r in self.rows:
                w.writerow([r.rating, r.date, r.content])

    # -----------------------------
    # Core loop
    # -----------------------------
    def _collect_loop(self, mode: str, wait: WebDriverWait, more_wait: WebDriverWait) -> None:
        """
        mode:
          - "hundred": 100자평 영역
          - "myreview": 마이리뷰 영역
        """
        assert self.driver is not None
        driver = self.driver

        # 탭 전환 후 카드 생성 대기(베스트 에포트)
        try:
            wait.until(lambda d: len(self._find_review_cards()) > 0)
        except TimeoutException:
            pass

        stagnation = 0
        last_count = len(self.rows)

        while len(self.rows) < self.TARGET_COUNT:
            cards = self._find_review_cards()
            self._extract_from_cards(cards, mode=mode)
            # _collect_loop while 안, extract 직후쯤
            self.logger.info(f"[{mode}] collected={len(self.rows)} visible_cards={len(cards)} unique={len(self.seen_ids)}")

            if len(self.rows) == last_count:
                stagnation += 1
            else:
                stagnation = 0
                last_count = len(self.rows)

            if len(self.rows) >= self.TARGET_COUNT:
                break

            ok = self._click_more_and_wait(more_wait, mode=mode, max_attempts=self.MORE_MAX_ATTEMPTS)
            if not ok:
                break

            time.sleep(0.8)

            if stagnation >= self.STAGNATION_LIMIT:
                break

        # 마이리뷰 쪽은 내부 +더보기로 전체 내용이 숨겨진 경우가 있어,
        # 최종적으로 아직 부족하면 보이는 카드들에 대해 "내부 +더보기" 한번 더 확장 시도
        if mode == "myreview" and len(self.rows) < self.TARGET_COUNT:
            try:
                self._expand_visible_myreview_contents(max_clicks=80)
                cards2 = self._find_review_cards()
                self._extract_from_cards(cards2, mode=mode)
            except Exception:
                pass

    # -----------------------------
    # DOM helpers (generic)
    # -----------------------------
    def _wait_ready_state(self, wait: WebDriverWait) -> None:
        assert self.driver is not None
        try:
            wait.until(lambda d: d.execute_script("return document.readyState") in ("interactive", "complete"))
        except Exception:
            pass

    def _scroll_until_review_area_visible(self, max_scrolls: int = 80) -> None:
        assert self.driver is not None
        driver = self.driver

        for _ in range(max_scrolls):
            if driver.find_elements(By.CSS_SELECTOR, "#tabTotal"):
                return
            if driver.find_elements(By.CSS_SELECTOR, "#tabMyReviewTotal"):
                return
            if driver.find_elements(By.CSS_SELECTOR, "div.hundred_list"):
                return
            if driver.find_elements(By.CSS_SELECTOR, "div.Ere_btn_more a[href*='fn_CommunityReviewMore']"):
                return
            if driver.find_elements(By.CSS_SELECTOR, "div.Ere_btn_more a[href*='fn_CommunityReviewMore_MyReview']"):
                return
            if driver.find_elements(By.CSS_SELECTOR, "div.Ere_btn_more a[href*='fn_MyReviewMore']"):
                return

            driver.execute_script("window.scrollBy(0, Math.max(700, window.innerHeight * 0.9));")
            time.sleep(0.25)

    def _find_review_cards(self) -> List[WebElement]:
        assert self.driver is not None
        return self.driver.find_elements(By.CSS_SELECTOR, "div.hundred_list")

    # -----------------------------
    # Tab switching
    # -----------------------------
    def _click_hundred_total_tab(self) -> None:
        """
        100자평 -> 전체 탭 전환.
        """
        assert self.driver is not None
        driver = self.driver

        # 1) id 클릭
        try:
            el = driver.find_element(By.CSS_SELECTOR, "#tabTotal")
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            time.sleep(0.2)
            driver.execute_script("arguments[0].click();", el)
            time.sleep(0.9)
            return
        except Exception:
            pass

        # 2) onclick 기반
        try:
            driver.execute_script(
                r"""
                try {
                  const links = Array.from(document.querySelectorAll("a[onclick*='fn_IsOrdererCommentReview']"));
                  const re = /,\s*2\s*,/;
                  const cand = links.find(a => re.test(a.getAttribute('onclick') || ''));
                  if (cand) cand.click();
                } catch(e) {}
                """
            )
            time.sleep(0.9)
        except Exception:
            pass

    def _click_myreview_total_tab(self) -> None:
        """
        마이리뷰 -> 전체 탭 전환.
        예: <a id="tabMyReviewTotal" ... onclick="fn_IsOrdererMyReview(2)">전체 (...)</a>
        """
        assert self.driver is not None
        driver = self.driver

        # 1) id 클릭
        try:
            el = driver.find_element(By.CSS_SELECTOR, "#tabMyReviewTotal")
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            time.sleep(0.2)
            driver.execute_script("arguments[0].click();", el)
            time.sleep(1.0)
            return
        except Exception:
            pass

        # 2) onclick 직접 호출
        try:
            driver.execute_script("try { fn_IsOrdererMyReview(2); } catch(e) {}")
            time.sleep(1.0)
        except Exception:
            pass

        # 3) onclick 탐색
        try:
            driver.execute_script(
                r"""
                try {
                  const links = Array.from(document.querySelectorAll("a[onclick*='fn_IsOrdererMyReview']"));
                  const cand = links.find(a => /fn_IsOrdererMyReview\(\s*2\s*\)/.test(a.getAttribute('onclick') || ''));
                  if (cand) cand.click();
                } catch(e) {}
                """
            )
            time.sleep(1.0)
        except Exception:
            pass

    # -----------------------------
    # "More" clicking (robust)
    # -----------------------------
    def _click_more_and_wait(self, wait: WebDriverWait, mode: str, max_attempts: int = 8) -> bool:
        """
        mode에 따라 더보기 함수/버튼이 달라질 수 있으므로,
        여러 후보를 순서대로 시도.
        성공 조건:
          - 카드 signature set 변화
          - 카드 개수 증가
        """
        assert self.driver is not None
        driver = self.driver

        backoff = [2, 4, 8, 12, 20, 30, 45, 60]

        for attempt in range(1, max_attempts + 1):
            before_cards = self._find_review_cards()
            before_n = len(before_cards)
            before_ids = self._visible_card_signatures(before_cards)

            # 버튼이 없으면(끝까지 로드됐을 가능성) 빠르게 종료 판단
            has_more_btn = self._has_more_button(mode)

            # 1) JS 함수 후보들
            self._try_more_js_calls(mode)

            # 2) 버튼 클릭 후보
            self._try_more_button_click(mode)

            # 변화 감지
            def changed(_: WebDriver) -> bool:
                cards = self._find_review_cards()
                if len(cards) > before_n:
                    return True
                cur_ids = self._visible_card_signatures(cards)
                return len(cur_ids - before_ids) > 0

            try:
                wait.until(changed)
                return True
            except TimeoutException:
                # 더보기 버튼도 없고, 변화도 없으면 종료
                if not has_more_btn:
                    return False

                # 약간 더 스크롤 + 백오프
                try:
                    driver.execute_script("window.scrollBy(0, Math.max(700, window.innerHeight * 0.9));")
                except Exception:
                    pass
                time.sleep(backoff[min(attempt - 1, len(backoff) - 1)])

        return False

    def _has_more_button(self, mode: str) -> bool:
        assert self.driver is not None
        driver = self.driver

        selectors: List[str] = []
        if mode == "hundred":
            selectors = [
                "div.Ere_btn_more a[href*='fn_CommunityReviewMore']",
                "a[href*='fn_CommunityReviewMore']",
            ]
        else:
            selectors = [
                "div.Ere_btn_more a[href*='fn_CommunityReviewMore_MyReview']",
                "div.Ere_btn_more a[href*='fn_MyReviewMore']",
                "a[href*='fn_CommunityReviewMore_MyReview']",
                "a[href*='fn_MyReviewMore']",
            ]

        for sel in selectors:
            try:
                if driver.find_elements(By.CSS_SELECTOR, sel):
                    return True
            except Exception:
                continue
        return False

    def _try_more_js_calls(self, mode: str) -> None:
        assert self.driver is not None
        driver = self.driver

        js_calls: List[str] = []
        if mode == "hundred":
            js_calls = [
                "try { fn_CommunityReviewMore(); } catch(e) {}",
                "try { fn_CommunityReviewMore( ); } catch(e) {}",
            ]
        else:
            js_calls = [
                "try { fn_CommunityReviewMore_MyReview(); } catch(e) {}",
                "try { fn_MyReviewMore(); } catch(e) {}",
            ]

        for js in js_calls:
            try:
                driver.execute_script(js)
            except Exception:
                continue

    def _try_more_button_click(self, mode: str) -> None:
        assert self.driver is not None
        driver = self.driver

        selectors: List[str] = []
        if mode == "hundred":
            selectors = [
                "div.Ere_btn_more a[href*='fn_CommunityReviewMore']",
                "a[href*='fn_CommunityReviewMore']",
            ]
        else:
            selectors = [
                "div.Ere_btn_more a[href*='fn_CommunityReviewMore_MyReview']",
                "div.Ere_btn_more a[href*='fn_MyReviewMore']",
                "a[href*='fn_CommunityReviewMore_MyReview']",
                "a[href*='fn_MyReviewMore']",
            ]

        for sel in selectors:
            try:
                btns = driver.find_elements(By.CSS_SELECTOR, sel)
                if not btns:
                    continue
                b = btns[0]
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", b)
                time.sleep(0.25)
                driver.execute_script("arguments[0].click();", b)
                return
            except Exception:
                continue

    # -----------------------------
    # Robust id/signature / extraction
    # -----------------------------
    def _visible_card_signatures(self, cards: List[WebElement]) -> Set[str]:
        ids: Set[str] = set()
        for c in cards:
            try:
                rid = self._extract_paper_id(c)
                if rid:
                    ids.add(f"id:{rid}")
                    continue
                # fallback: textContent md5
                txt = (c.get_attribute("textContent") or "").strip()
                if txt:
                    ids.add("md5:" + hashlib.md5(txt.encode("utf-8")).hexdigest())
            except Exception:
                continue
        return ids

    def _extract_from_cards(self, cards: List[WebElement], mode: str) -> int:
        added = 0
        for card in cards:
            if len(self.rows) >= self.TARGET_COUNT:
                break

            try:
                row, rid = self._parse_one_card(card, mode=mode)
                if not rid:
                    continue
                if not row.content:
                    continue
                if rid in self.seen_ids:
                    continue

                self.seen_ids.add(rid)
                self.rows.append(row)
                added += 1

            except StaleElementReferenceException:
                continue
            except Exception:
                continue

        return added

    def _parse_one_card(self, card: WebElement, mode: str) -> Tuple[ReviewRow, str]:
        rid = self._extract_paper_id(card)
        rating = self._extract_rating(card)
        date = self._extract_date(card)
        content = self._extract_content(card, mode=mode)

        date = date.replace("\xa0", " ").strip()
        content = content.replace("\xa0", " ").strip()

        if not rid:
            sig = f"{date}|{rating}|{content}"
            rid = hashlib.md5(sig.encode("utf-8")).hexdigest()

        return ReviewRow(rating=rating, date=date, content=content), rid

    # -----------------------------
    # Field extractors (shared)
    # -----------------------------
    def _extract_paper_id(self, card: WebElement) -> str:
        # 1) 100자평 토글 onclick
        try:
            el = card.find_element(By.XPATH, ".//*[@onclick and contains(@onclick,'fn_ToggleCommentReviewPaper')]")
            onclick = el.get_attribute("onclick") or ""
            m = re.search(r"fn_ToggleCommentReviewPaper\('(\d+)'\)", onclick)
            if m:
                return m.group(1)
        except Exception:
            pass

        # 2) 마이리뷰 토글 onclick
        try:
            el = card.find_element(By.XPATH, ".//*[@onclick and contains(@onclick,'fn_ToggleMyReviewPaper')]")
            onclick = el.get_attribute("onclick") or ""
            m = re.search(r"fn_ToggleMyReviewPaper\(\s*(\d+)\s*,", onclick)
            if m:
                return m.group(1)
        except Exception:
            pass

        # 3) 마이리뷰 쇼 onclick
        try:
            el = card.find_element(By.XPATH, ".//*[@onclick and contains(@onclick,'fn_show_mypaper_utf8')]")
            onclick = el.get_attribute("onclick") or ""
            m = re.search(r"fn_show_mypaper_utf8\(\s*(\d+)\s*,", onclick)
            if m:
                return m.group(1)
        except Exception:
            pass

        # 4) span id
        try:
            spans = card.find_elements(By.CSS_SELECTOR, "span[id^='spnPaper']")
            for sp in spans:
                sid = sp.get_attribute("id") or ""
                m = re.fullmatch(r"spnPaper(\d+)", sid)
                if m:
                    return m.group(1)
        except Exception:
            pass

        # 5) div id
        try:
            divs = card.find_elements(By.CSS_SELECTOR, "div[id^='div_commentReviewPaper']")
            for dv in divs:
                did = dv.get_attribute("id") or ""
                m = re.search(r"div_commentReviewPaper(\d+)", did)
                if m:
                    return m.group(1)
        except Exception:
            pass

        # 6) myreview short/all ids
        try:
            divs = card.find_elements(By.CSS_SELECTOR, "div[id^='paperShort_'], div[id^='paperAll_'], div[id^='divPaper']")
            for dv in divs:
                did = dv.get_attribute("id") or ""
                m = re.search(r"(\d+)", did)
                if m:
                    return m.group(1)
        except Exception:
            pass

        return ""

    def _extract_rating(self, card: WebElement) -> str:
        try:
            imgs = card.find_elements(By.CSS_SELECTOR, ".HL_star img")
            on = 0
            for im in imgs:
                src = (im.get_attribute("src") or "").lower()
                if "icon_star_on" in src:
                    on += 1
            if on > 0:
                return str(on)
        except Exception:
            pass

        # fallback: 카드 텍스트에 별점 숫자가 섞이는 경우 방어(드물지만)
        try:
            txt = (card.get_attribute("textContent") or "")
            m = re.search(r"별점\s*([1-5])", txt)
            if m:
                return m.group(1)
        except Exception:
            pass

        return ""

    def _extract_date(self, card: WebElement) -> str:
        try:
            spans = card.find_elements(By.CSS_SELECTOR, ".left span")
            for sp in spans:
                t = (sp.text or "").strip()
                if re.fullmatch(r"\d{4}-\d{2}-\d{2}", t):
                    return t
        except Exception:
            pass

        try:
            txt = card.get_attribute("textContent") or ""
            m = re.search(r"(\d{4}-\d{2}-\d{2})", txt)
            if m:
                return m.group(1)
        except Exception:
            pass

        return ""

    def _extract_content(self, card: WebElement, mode: str) -> str:
        """
        mode="hundred": spnPaper{digits} 텍스트를 우선
        mode="myreview": paperShort_ / divPaper{digits} 우선, 필요시 내부 +더보기 클릭/JS 호출로 확장 시도
        """
        assert self.driver is not None
        driver = self.driver

        if mode == "hundred":
            # 1) spnPaper*
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

            # 2) 토글 클릭 후 재시도
            try:
                toggle = card.find_element(By.XPATH, ".//*[@onclick and contains(@onclick,'fn_ToggleCommentReviewPaper')]")
                try:
                    driver.execute_script("arguments[0].click();", toggle)
                    time.sleep(0.35)
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

        else:
            # 1) paperShort_ 안의 divPaper{digits}
            try:
                divs = card.find_elements(By.CSS_SELECTOR, "div[id^='paperShort_'] div[id^='divPaper']")
                for dv in divs:
                    t = (dv.get_attribute("textContent") or "").strip()
                    if t:
                        return self._strip_myreview_tail(t)
            except Exception:
                pass

            # 2) short 박스 자체
            try:
                divs = card.find_elements(By.CSS_SELECTOR, "div[id^='paperShort_']")
                for dv in divs:
                    t = (dv.get_attribute("textContent") or "").strip()
                    if t:
                        return self._strip_myreview_tail(t)
            except Exception:
                pass

            # 3) + 더보기 클릭(있으면)
            try:
                more = card.find_element(By.CSS_SELECTOR, "a[onclick*='fn_show_mypaper_utf8']")
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", more)
                    time.sleep(0.2)
                    driver.execute_script("arguments[0].click();", more)
                    time.sleep(0.8)
                except Exception:
                    pass

                # paperAll_{id}에 내용이 채워졌는지 확인
                divs = card.find_elements(By.CSS_SELECTOR, "div.paper-contents[id^='paperAll_']")
                for dv in divs:
                    t = (dv.get_attribute("textContent") or "").strip()
                    if t:
                        return t
            except Exception:
                pass

        # 마지막 fallback: 카드 전체 textContent
        try:
            txt = (card.get_attribute("textContent") or "").strip()
            return re.sub(r"\s+", " ", txt)
        except Exception:
            return ""

    def _strip_myreview_tail(self, text: str) -> str:
        # " + 더보기" 같은 꼬리 제거
        t = re.sub(r"\+\s*더보기\s*$", "", text).strip()
        t = re.sub(r"\s+", " ", t).strip()
        return t

    def _expand_visible_myreview_contents(self, max_clicks: int = 80) -> None:
        """
        현재 화면에 보이는 마이리뷰 카드들에서, "+ 더보기" 링크를 가능한 만큼 눌러
        paperAll_*에 내용을 채우도록 시도.
        """
        assert self.driver is not None
        driver = self.driver

        clicks = 0
        cards = self._find_review_cards()
        for card in cards:
            if clicks >= max_clicks:
                break
            try:
                links = card.find_elements(By.CSS_SELECTOR, "a[onclick*='fn_show_mypaper_utf8']")
                if not links:
                    continue
                a = links[0]
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", a)
                time.sleep(0.15)
                driver.execute_script("arguments[0].click();", a)
                clicks += 1
                time.sleep(0.3)
            except Exception:
                continue


if __name__ == "__main__":
    # Local single-file test:
    # python review_analysis/crawling/aladin_crawler.py
    here = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.abspath(os.path.join(here, "..", "..", "database"))

    crawler = AladinCrawler(out_dir)
    crawler.scrape_reviews()
    crawler.save_to_database()
