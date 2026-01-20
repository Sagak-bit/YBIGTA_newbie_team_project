import re
from pathlib import Path
from typing import Optional, cast

import numpy as np
import pandas as pd

# headless 환경에서도 저장 가능하게 설정
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.feature_extraction.text import TfidfVectorizer

from review_analysis.preprocessing.base_processor import BaseDataProcessor


class AladinProcessor(BaseDataProcessor):
    """
    Input : ../../database/reviews_aladin.csv (columns: rating, date, content)
    Output: {output_dir}/preprocessed_reviews_aladin.csv
    Plots : review_analysis/plots/*.png
    """

    def __init__(self, input_path: str, output_dir: str):
        super().__init__(input_path, output_dir)
        self.df_pre: Optional[pd.DataFrame] = None
        self.df_fe: Optional[pd.DataFrame] = None

        # 규칙(명세 대응)
        self.rating_min = 1
        self.rating_max = 5
        self.min_text_len = 5
        self.tfidf_max_features = 200

        # 텍스트 정제용 정규식
        self._space_re = re.compile(r"\s+")
        # 한/영/숫자/공백/기본 문장부호만 남기기 (너무 공격적이면 완화 가능)
        self._keep_re = re.compile(r"[^0-9A-Za-z가-힣\s\.\,\!\?\:\;\-\(\)\[\]\"\'/]+")

    # -------------------------
    # Preprocess
    # -------------------------
    def preprocess(self) -> None:
        df = self._read_csv_robust(self.input_path)

        required = {"rating", "date", "content"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {sorted(missing)}")

        # 결측 제거(가장 안전)
        df = df.dropna(subset=["rating", "date", "content"]).copy()

        # 타입 정리
        df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["content"] = df["content"].astype(str)

        df = df.dropna(subset=["rating", "date"]).copy()

        # 별점 이상치 제거
        df = df[(df["rating"] >= self.rating_min) & (df["rating"] <= self.rating_max)].copy()

        # 미래 날짜 제거(방어 로직)
        today = pd.Timestamp.today().normalize()
        df = df[df["date"] <= today].copy()

        # 텍스트 정제 + 길이 파생
        df["content_clean"] = df["content"].map(self._clean_text)
        df["content_len"] = df["content_clean"].str.len()

        # 너무 짧은 리뷰 제거
        df = df[df["content_len"] >= self.min_text_len].copy()

        df = df.reset_index(drop=True)
        self.df_pre = df

        # EDA 플롯 저장(명세 대응)
        self._save_eda_plots(df)

    def _read_csv_robust(self, path: str) -> pd.DataFrame:
        # 인코딩 이슈 방어
        for enc in ("utf-8-sig", "utf-8"):
            try:
                return pd.read_csv(path, encoding=enc)
            except UnicodeDecodeError:
                continue
        # 마지막 fallback
        return pd.read_csv(path)

    def _clean_text(self, text: str) -> str:
        t = self._keep_re.sub(" ", text)
        t = self._space_re.sub(" ", t).strip()
        return t

    # -------------------------
    # Feature Engineering
    # -------------------------
    def feature_engineering(self) -> None:
        if self.df_pre is None:
            raise RuntimeError("preprocess() must be called before feature_engineering().")

        df = self.df_pre.copy()

        # dt 접근을 IDE/type checker가 확정적으로 인식하게 함
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"]).copy()

        date_s = df["date"].astype("datetime64[ns]")

        # 파생변수(명세: 1개 이상)
        df["year"] = date_s.dt.year
        df["month"] = date_s.dt.month
        df["weekday"] = date_s.dt.dayofweek  # 월=0 ... 일=6
        df["is_weekend"] = (df["weekday"] >= 5).astype(int)
        df["year_month"] = date_s.dt.to_period("M").astype(str)

        # 텍스트 벡터화(TF-IDF)
        vectorizer = TfidfVectorizer(
            max_features=self.tfidf_max_features,
            ngram_range=(1, 2),
            tokenizer=self._simple_tokenize,
            token_pattern=None,  # tokenizer를 직접 쓰므로 필요
            lowercase=False,
        )

        tfidf = vectorizer.fit_transform(df["content_clean"].tolist())
        feats = list(vectorizer.get_feature_names_out())

        # IDE 타입 경고(빨간줄) 방지용: toarray() 결과를 ndarray로 명시
        tfidf_mat = cast(np.ndarray, tfidf.toarray())
        tfidf_df = pd.DataFrame(tfidf_mat, columns=[f"tfidf__{f}" for f in feats])
        tfidf_df.index = df.index

        df = pd.concat([df, tfidf_df], axis=1)
        self.df_fe = df

    def _simple_tokenize(self, s: str) -> list[str]:
        # 공백 기반 토큰화(의존성 최소, 과제 안정성 높음)
        toks = [t for t in s.split() if len(t) >= 2]
        return toks

    # -------------------------
    # Save
    # -------------------------
    def save_to_database(self) -> None:
        if self.df_fe is None:
            raise RuntimeError("feature_engineering() must be called before save_to_database().")

        out_dir = Path(self.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        out_path = out_dir / "preprocessed_reviews_aladin.csv"
        self.df_fe.to_csv(out_path, index=False, encoding="utf-8-sig")

    # -------------------------
    # Plot helpers
    # -------------------------
    def _plots_dir(self) -> Path:
        """
        review_analysis/plots 를 '레포 루트 기준'으로 찾고,
        못 찾으면 현재 파일 기준으로 생성(최소한 저장은 되게).
        """
        here = Path(__file__).resolve()

        # 위로 올라가면서 review_analysis 폴더가 있는 지점을 찾음
        for p in [here] + list(here.parents):
            cand = p / "review_analysis"
            if cand.is_dir():
                plots = cand / "plots"
                plots.mkdir(parents=True, exist_ok=True)
                return plots

        # fallback: 현재 파일 위치 기준
        fallback = here.parent / "plots"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback

    def _save_eda_plots(self, df: pd.DataFrame) -> None:
        plots_dir = self._plots_dir()

        # 1) 별점 분포
        plt.figure()
        df["rating"].hist(bins=5)
        plt.title("Aladin: Rating Distribution")
        plt.xlabel("rating")
        plt.ylabel("count")
        plt.tight_layout()
        plt.savefig(plots_dir / "aladin_rating_hist.png", dpi=200)
        plt.close()

        # 2) 텍스트 길이 분포
        plt.figure()
        df["content_len"].hist(bins=30)
        plt.title("Aladin: Text Length Distribution")
        plt.xlabel("content_len")
        plt.ylabel("count")
        plt.tight_layout()
        plt.savefig(plots_dir / "aladin_textlen_hist.png", dpi=200)
        plt.close()

        # 3) 월별 리뷰 수(시계열)
        plt.figure()
        monthly = df.set_index("date").resample("ME").size()  # 'M' deprecated 대응
        monthly.plot()
        plt.title("Aladin: Monthly Review Count")
        plt.xlabel("month")
        plt.ylabel("count")
        plt.tight_layout()
        plt.savefig(plots_dir / "aladin_monthly_count.png", dpi=200)
        plt.close()
