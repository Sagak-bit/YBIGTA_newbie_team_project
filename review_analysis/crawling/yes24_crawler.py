from __future__ import annotations

import os
import re
import time
import csv
from typing import Dict, List, Optional, Set
from urllib.parse import urlencode

from bs4 import BeautifulSoup
from bs4.element import Tag

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from review_analysis.crawling.base_crawler import BaseCrawler
from utils.logger import setup_logger


class Yes24Crawler(BaseCrawler):
    """
    YES24의 소년이 온다 리뷰를 Selenium으로 크롤링하는 클래스.
    전체 리뷰 -> 추천순 항목에 접속하여
    550개의 리뷰를 수집한다.
    """


    def __init__(self, output_dir: str):
        super().__init__(output_dir)
        self.base_url: str = "https://www.yes24.com/Product/Goods/13137546"
        self.logger = setup_logger("yes24_crawler.log")
        self.reviews_data: List[Dict[str, str]] = []
        self.driver: Optional[webdriver.Chrome] = None

        self.target_count: int = 550
        self.sort: str = "2"  

    def start_browser(self) -> None:
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--lang=ko-KR")
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.logger.info("크롬 브라우저를 실행합니다.")

    def scrape_reviews(self) -> None:
        """
        Selenium으로 YES24 리뷰 HTML 조각 엔드포인트를 직접 열고(driver.get),
        page_source를 BeautifulSoup로 파싱해서 수집한다.
        리뷰는 중복 제거하면서 self.target_count개까지 수집을 시도한다.
        """
        if self.driver is None:
            self.start_browser()
        assert self.driver is not None

        wait = WebDriverWait(self.driver, 20)

        goods_no_match = re.search(r"/Goods/(\d+)", self.base_url)
        if not goods_no_match:
            self.logger.error("base_url에서 goods_no를 추출하지 못했습니다.")
            return
        goods_no: str = goods_no_match.group(1)

        try:
            self.driver.get(self.base_url)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(0.5)
            html: str = self.driver.page_source
        except Exception as e:
            self.logger.error(f"상품 페이지 로드 실패: {e}")
            return

        goods_sort_no: Optional[str] = None
        goods_gb: Optional[str] = None

        m1 = re.search(r"goodsSortNo=(\d+)", html)
        m2 = re.search(r"goodsGb=(\d+)", html)
        if m1:
            goods_sort_no = m1.group(1)
        if m2:
            goods_gb = m2.group(1)

        if goods_sort_no is None:
            goods_sort_no = "001033"
            self.logger.warning("goodsSortNo 추출 실패 -> 기본값 001033 사용")
        if goods_gb is None:
            goods_gb = "01"
            self.logger.warning("goodsGb 추출 실패 -> 기본값 01 사용")

        review_base_url: str = f"https://www.yes24.com/Product/CommunityModules/GoodsReviewList/{goods_no}"

        base_params: Dict[str, str] = {
            "goodsSortNo": goods_sort_no,
            "goodsGb": goods_gb,
            "type": "ALL",
            "DoJungAfterBuy": "0",
            "Sort": self.sort,  # 1=최근순, 2=추천순(추정)
        }

        seen: Set[str] = set()
        page: int = 1

        while len(self.reviews_data) < self.target_count:
            self.logger.info(
                f"--- {page}페이지 수집 중 (현재 수집량: {len(self.reviews_data)}/{self.target_count}) ---"
            )

            params = dict(base_params)
            params["PageNumber"] = str(page)
            url = f"{review_base_url}?{urlencode(params)}"

            try:
                self.driver.get(url)
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".reviewInfoGrp")))
            except Exception as e:
                self.logger.error(f"리뷰 페이지 로드 실패 (page={page}): {e}")
                break

            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            review_groups = soup.select(".reviewInfoGrp")

            if not review_groups:
                self.logger.info(f"{page}페이지에 리뷰가 없어서 종료합니다.")
                break

            added_this_page = 0

            for group in review_groups:
                if not isinstance(group, Tag):
                    continue

                try:
                    # 별점 (0~5)
                    rating: str = "5"
                    rating_elem = group.select_one(".review_rating .total_rating")
                    if isinstance(rating_elem, Tag):
                        classes_raw = rating_elem.get("class")
                        classes: List[str] = []
                        if isinstance(classes_raw, list):
                            classes = [c for c in classes_raw if isinstance(c, str)]
                        elif isinstance(classes_raw, str):
                            classes = [classes_raw]

                        for cls in classes:
                            if "total_rating_" in cls:
                                rating = str(int(cls.split("_")[-1]) // 2)
                                break

                    # 날짜
                    date: str = ""
                    date_elem = group.select_one("em.txt_date")
                    if isinstance(date_elem, Tag):
                        date = date_elem.get_text(strip=True)

                    # 내용
                    content: str = ""
                    content_elem = group.select_one(".reviewInfoBot.origin .review_cont")
                    if isinstance(content_elem, Tag):
                        content = content_elem.get_text(strip=True)

                    # 중복 제거(수집 단계)
                    if content and content not in seen:
                        seen.add(content)
                        self.reviews_data.append({"rating": rating, "date": date, "content": content})
                        added_this_page += 1

                    if len(self.reviews_data) >= self.target_count:
                        break

                except Exception as e:
                    self.logger.error(f"파싱 오류: {e}")

            self.logger.info(f"{page}페이지에서 신규 {added_this_page}개 추가됨")

            page += 1
            time.sleep(0.2)

        self.logger.info(f"수집 종료: 총 {len(self.reviews_data)}개 수집됨 (목표 {self.target_count})")

        try:
            self.driver.quit()
        except Exception:
            pass
        self.driver = None

    def save_to_database(self) -> None:
        """
        리뷰를 csv로 저장 (의존성 최소).
        content 기준으로 최종 중복 제거 후 저장.
        """
        if not self.reviews_data:
            return

        os.makedirs(self.output_dir, exist_ok=True)
        file_path = os.path.join(self.output_dir, "reviews_yes24.csv")

        seen: Set[str] = set()
        rows: List[Dict[str, str]] = []
        for r in self.reviews_data:
            c = r.get("content", "")
            if c and c not in seen:
                seen.add(c)
                rows.append(r)

        with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["rating", "date", "content"])
            writer.writeheader()
            writer.writerows(rows)

        self.logger.info(f"CSV 저장 완료: {file_path}")
