from __future__ import annotations

import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import pandas as pd
from selenium import webdriver
from selenium.common.exceptions import (
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from review_analysis.crawling.base_crawler import BaseCrawler
from utils.logger import setup_logger


@dataclass(frozen=True, slots=True)
class ReviewRow:
    """
    A normalized review record.

    Attributes
    ----------
    date:
        Review creation date in ISO-like format: YYYY-MM-DD.
    content:
        Review text content. Newlines may be preserved.
    rating:
        Rating score on a 0.0-10.0 scale derived from the filled indicator width.
    """

    date: str
    content: str
    rating: float


class KyoboCrawler(BaseCrawler):
    """
    Crawl Kyobo product reviews and save them as a CSV file.

    Notes
    -----
    - This crawler targets the Kyobo product detail page review section.
    - It collects at least 500 reviews and guarantees the required fields:
      date, content, and rating.
    - It attempts to use "Latest" sort order when available.
    - It performs periodic checkpoint saves to reduce data loss on failures.

    Output
    ------
    A CSV file is written to:
        {output_dir}/reviews_kyobo.csv
    """

    BASE_URL = "https://product.kyobobook.co.kr/detail/S000000610612"
    OUTPUT_NAME = "reviews_kyobo.csv"

    DATE_PATTERN = re.compile(r"\d{4}\.\d{2}\.\d{2}")
    WIDTH_PATTERN = re.compile(r"width:\s*([\d.]+)%")

    REVIEW_TAB_SEL = 'a.tab_link[href="#scrollSpyProdReview"]'
    REVIEW_ANCHOR_SEL = "#scrollSpyProdReview"
    REVIEW_ITEM_SEL = ".comment_item"

    SORT_BTN_SEL = "#ui-id-31-button"
    SORT_MENU_SEL = "#ui-id-31-menu"

    NEXT_BTN_SEL = "button.btn_page.next"

    def __init__(self, output_dir: str) -> None:
        """
        Initialize the crawler.

        Parameters
        ----------
        output_dir:
            Directory path where output CSV files will be written.
        """
        super().__init__(output_dir)
        self.logger = setup_logger("kyobo.log")
        self.driver: Optional[webdriver.Chrome] = None
        self.rows: list[ReviewRow] = []
        self._seen: set[tuple[str, str]] = set()

    def start_browser(self) -> None:
        """
        Start a Chrome session and navigate to the product page.

        Notes
        -----
        Uses webdriver-manager to resolve the appropriate chromedriver.
        """
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service)
        self.driver.get(self.BASE_URL)

    def scrape_reviews(self) -> None:
        """
        Execute the end-to-end crawling pipeline.

        Steps
        -----
        1) Start browser and open product page.
        2) Open the review section tab.
        3) Switch sort order (best effort).
        4) Paginate and collect reviews until the target is reached.
        5) Save results as CSV (with periodic checkpoints).
        """
        target = 600
        checkpoint_every_pages = 3

        self.start_browser()
        assert self.driver is not None

        page_no = 0
        try:
            self._open_review_tab()

            # Best-effort: sorting can be flaky; crawling should still proceed.
            self._set_sort_order("최신순")

            while len(self.rows) < target:
                page_no += 1

                self._scrape_current_page(target)
                if len(self.rows) >= target:
                    break

                self._move_to_next_page()

                if page_no % checkpoint_every_pages == 0:
                    self._save_checkpoint()

            self.save_to_database()
            self.logger.info("Saved %d reviews", len(self.rows))
        except Exception as exc:
            self.logger.exception("Crawl failed: %s", exc)
            self._save_checkpoint()
            raise
        finally:
            self._shutdown()

    def save_to_database(self) -> None:
        """
        Save collected reviews to a CSV file in the output directory.

        Notes
        -----
        Output encoding is UTF-8 with BOM for Excel-friendly behavior on Windows.
        """
        out_dir = Path(self.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        out_path = out_dir / self.OUTPUT_NAME
        df = pd.DataFrame([asdict(r) for r in self.rows])
        df.to_csv(out_path, encoding="utf-8-sig", index=False)

    def _shutdown(self) -> None:
        """
        Shutdown the web driver session safely.

        This method is idempotent and safe to call multiple times.
        """
        if self.driver is None:
            return

        try:
            self.driver.quit()
        except Exception:
            pass

        self.driver = None

    def _save_checkpoint(self) -> None:
        """
        Persist a checkpoint CSV to reduce data loss on failures.

        Notes
        -----
        Uses the final output path so reruns overwrite deterministically.
        """
        try:
            self.save_to_database()
            self.logger.info("Checkpoint saved (%d reviews)", len(self.rows))
        except Exception:
            self.logger.warning("Checkpoint save failed")

    def _open_review_tab(self) -> None:
        """
        Navigate to the review section and ensure the list UI is present.

        Guarantees
        ----------
        - Review tab is clicked.
        - Review header container exists.
        - At least one review element is present.
        """
        assert self.driver is not None

        review_tab = WebDriverWait(self.driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, self.REVIEW_TAB_SEL))
        )
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});", review_tab
        )
        self.driver.execute_script("arguments[0].click();", review_tab)

        WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".tab_list_wrap"))
        )
        WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, self.REVIEW_ITEM_SEL))
        )

    def _set_sort_order(self, order_text: str = "최신순") -> None:
        """
        Set the review sort order via the jQuery UI selectmenu control.

        Parameters
        ----------
        order_text:
            Visible option text to select (e.g., "최신순" or "좋아요 순").

        Raises
        ------
        TimeoutException
            If the control exists but lacks a usable id binding (unexpected DOM).
        """
        assert self.driver is not None
        wait = WebDriverWait(self.driver, 20)

        # Ensure header area is rendered (tabs + sort control).
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".tab_list_wrap")))
        wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, ".tab_list_wrap .right_area")
            )
        )

        def locate_button(d: webdriver.Chrome) -> Optional[WebElement]:
            """
            Locate the jQuery UI selectmenu button element.

            Returns
            -------
            Optional[WebElement]
                The most suitable selectmenu button if found, otherwise None.
            """
            candidates = d.find_elements(
                By.CSS_SELECTOR, "span[role='combobox'].ui-selectmenu-button"
            )
            if not candidates:
                return None

            # Prefer a button that already has visible text.
            for c in candidates:
                txt = c.find_elements(By.CSS_SELECTOR, ".ui-selectmenu-text")
                if txt and txt[0].text.strip():
                    return c

            return candidates[0]

        btn = wait.until(locate_button)
        assert btn is not None  # wait.until guarantees non-None

        cur = btn.find_element(By.CSS_SELECTOR, ".ui-selectmenu-text").text.strip()
        if cur == order_text:
            return

        # Open dropdown.
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
        self.driver.execute_script("arguments[0].click();", btn)

        btn_id = btn.get_attribute("id") or ""
        if not btn_id:
            raise TimeoutException("Sort button id missing")

        menu_sel = f"ul[role='listbox'][aria-labelledby='{btn_id}']"
        menu = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, menu_sel)))

        opt = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    (
                        f"//ul[@aria-labelledby='{btn_id}']"
                        f"//div[@role='option' and normalize-space()='{order_text}']"
                    ),
                )
            )
        )

        try:
            ActionChains(self.driver).move_to_element(opt).pause(0.05).click(opt).perform()
        except Exception:
            self.driver.execute_script("arguments[0].click();", opt)

        wait.until(lambda _: menu.get_attribute("aria-hidden") == "true")
        wait.until(
            lambda d: locate_button(d)
            .find_element(By.CSS_SELECTOR, ".ui-selectmenu-text")
            .text.strip()
            == order_text
        )

    def _scrape_current_page(self, target: int) -> None:
        """
        Scrape review items from the current page.

        Parameters
        ----------
        target:
            Global target number of reviews. Scraping stops early if reached.

        Notes
        -----
        - De-duplicates using (date, content).
        - Skips stale elements (DOM refresh resilience).
        """
        assert self.driver is not None

        WebDriverWait(self.driver, 20).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, self.REVIEW_ITEM_SEL))
        )

        items = self.driver.find_elements(By.CSS_SELECTOR, self.REVIEW_ITEM_SEL)

        for el in items:
            if len(self.rows) >= target:
                return

            try:
                row = self._parse_review(el)
            except StaleElementReferenceException:
                continue

            if row is None:
                continue

            key = (row.date, row.content)
            if key in self._seen:
                continue

            self._seen.add(key)
            self.rows.append(row)

    def _parse_review(self, el: WebElement) -> Optional[ReviewRow]:
        """
        Parse a single review DOM element into a ReviewRow.

        Parameters
        ----------
        el:
            Selenium WebElement representing one review item.

        Returns
        -------
        Optional[ReviewRow]
            Parsed review row if the required fields are found, otherwise None.
        """
        full_text = (el.text or "").strip()
        date_str = self._extract_date(full_text)
        if date_str is None:
            return None

        content = ""
        content_els = el.find_elements(By.CLASS_NAME, "comment_text")
        if content_els:
            content = (content_els[0].text or "").strip()

        rating = self._extract_rating_10(el)
        return ReviewRow(date=date_str, content=content, rating=rating)

    def _extract_date(self, text: str) -> Optional[str]:
        """
        Extract a date string from a text block.

        Parameters
        ----------
        text:
            Raw text that may include a date in 'YYYY.MM.DD' format.

        Returns
        -------
        Optional[str]
            'YYYY-MM-DD' if found, otherwise None.
        """
        m = self.DATE_PATTERN.search(text)
        if not m:
            return None
        return m.group(0).replace(".", "-")

    def _extract_rating_10(self, el: WebElement) -> float:
        """
        Extract the rating on a 10-point scale from a review element.

        Parameters
        ----------
        el:
            Selenium WebElement representing one review item.

        Returns
        -------
        float
            Rating in [0.0, 10.0]. Returns 0.0 if missing.
        """
        filled = el.find_elements(By.CLASS_NAME, "filled-stars")
        if not filled:
            return 0.0

        style = filled[0].get_attribute("style") or ""
        m = self.WIDTH_PATTERN.search(style)
        if not m:
            return 0.0

        pct = float(m.group(1))
        return round(pct / 10.0, 1)

    def _move_to_next_page(self) -> None:
        """
        Paginate to the next review page and wait for the list to refresh.

        Notes
        -----
        Uses the first review text as a page-change marker.
        """
        assert self.driver is not None

        old_marker = self._first_review_marker()

        next_btn = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, self.NEXT_BTN_SEL))
        )
        self._scroll_center(next_btn)
        self._safe_click(next_btn)

        self._wait_first_marker_change(old_marker)

        anchor = self.driver.find_element(By.CSS_SELECTOR, self.REVIEW_ANCHOR_SEL)
        self._scroll_start(anchor)
        time.sleep(0.15)

    def _first_review_marker(self) -> str:
        """
        Get a stable marker string for detecting page changes.

        Returns
        -------
        str
            The visible text of the first review item.
        """
        assert self.driver is not None

        first = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, self.REVIEW_ITEM_SEL))
        )
        try:
            return (first.text or "").strip()
        except StaleElementReferenceException:
            first = self.driver.find_element(By.CSS_SELECTOR, self.REVIEW_ITEM_SEL)
            return (first.text or "").strip()

    def _wait_first_marker_change(self, old_marker: str) -> None:
        """
        Wait until the first review marker changes (page refresh completed).

        Parameters
        ----------
        old_marker:
            The marker captured before clicking the next button.
        """
        assert self.driver is not None

        def changed(d: webdriver.Chrome) -> bool:
            try:
                now = d.find_element(By.CSS_SELECTOR, self.REVIEW_ITEM_SEL).text.strip()
                return now != old_marker
            except StaleElementReferenceException:
                return False

        WebDriverWait(self.driver, 10).until(changed)

    def _safe_click(self, el: WebElement) -> None:
        """
        Click an element with ActionChains and fall back to JS click.

        Parameters
        ----------
        el:
            Element to click.
        """
        assert self.driver is not None

        try:
            ActionChains(self.driver).move_to_element(el).pause(0.05).click(el).perform()
        except Exception:
            self._js_click(el)

    def _scroll_center(self, el: WebElement) -> None:
        """
        Scroll the given element into the center of the viewport.

        Parameters
        ----------
        el:
            Element to bring into view.
        """
        assert self.driver is not None
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)

    def _scroll_start(self, el: WebElement) -> None:
        """
        Scroll the given element to the top of the viewport.

        Parameters
        ----------
        el:
            Element to align at the viewport start.
        """
        assert self.driver is not None
        self.driver.execute_script("arguments[0].scrollIntoView({block:'start'});", el)

    def _js_click(self, el: WebElement) -> None:
        """
        Click an element using JavaScript.

        Parameters
        ----------
        el:
            Element to click.
        """
        assert self.driver is not None
        self.driver.execute_script("arguments[0].click();", el)