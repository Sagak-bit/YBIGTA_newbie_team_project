from __future__ import annotations

import os
import re
from typing import Optional

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from review_analysis.preprocessing.base_processor import BaseDataProcessor


class KyoboProcessor(BaseDataProcessor):
    """
    Kyobo review data processor.

    This processor performs:
    - EDA-friendly cleaning (nulls/outliers)
    - Text normalization
    - Feature engineering (length/time features, TF-IDF summaries)
    - Saving results into a CSV file under the database folder
    """

    SITE_NAME = "kyobo"

    def __init__(self, input_path: str, output_path: str) -> None:
        """
        Initialize the processor.

        Parameters
        ----------
        input_path:
            Path to the raw review CSV file (e.g., reviews_kyobo.csv).
        output_path:
            Directory path where processed CSV files will be written.
        """
        super().__init__(input_path, output_path)
        self.df: pd.DataFrame = pd.read_csv(input_path)
        self._tfidf: Optional[TfidfVectorizer] = None

        print(f"[Init] Loaded rows: {len(self.df)}")

    def preprocess(self) -> None:
        """
        Clean raw records.

        This step:
        - Removes rows with missing critical fields
        - Converts date/rating types safely
        - Drops rating outliers (keeps [0, 10])
        - Removes future-dated rows
        - Normalizes and cleans text
        - Drops empty text after cleaning
        - Deduplicates exact duplicates

        Notes
        -----
        The result is stored in `self.df` in-place.
        """
        original_len = len(self.df)

        # 1) Drop nulls in critical fields
        self.df.dropna(subset=["content", "date", "rating"], inplace=True)

        # 2) Safe type conversions (invalid -> NaT/NaN)
        self.df["date"] = pd.to_datetime(self.df["date"], errors="coerce")
        self.df["rating"] = pd.to_numeric(self.df["rating"], errors="coerce")
        self.df.dropna(subset=["date", "rating"], inplace=True)

        # 3) Rating outliers
        self.df = self.df[(self.df["rating"] >= 0) & (self.df["rating"] <= 10)]

        # 4) Drop future-dated rows
        today = pd.Timestamp.now()
        self.df = self.df[self.df["date"] <= today]

        # 5) Text cleaning
        def clean_text(text: object) -> str:
            """
            Normalize a raw text to a basic cleaned string.

            Parameters
            ----------
            text:
                Raw text-like object.

            Returns
            -------
            str
                Cleaned text with only Korean/English/digits/spaces preserved.
            """
            s = str(text)
            s = re.sub(r"[^가-힣a-zA-Z0-9\s]", " ", s)
            s = re.sub(r"\s+", " ", s).strip()
            return s

        self.df["cleaned_content"] = self.df["content"].apply(clean_text)

        # 6) Drop empty after cleaning
        self.df = self.df[self.df["cleaned_content"] != ""]

        # 7) Deduplicate
        self.df = self.df.drop_duplicates(subset=["date", "rating", "cleaned_content"])

        removed = original_len - len(self.df)
        print(f"[Preprocess] {original_len} -> {len(self.df)} (removed {removed})")

        # Quick sanity summary
        if len(self.df) > 0:
            print(
                "[Summary] date range:",
                self.df["date"].min().date(),
                "~",
                self.df["date"].max().date(),
            )
            print(
                "[Summary] rating range:",
                float(self.df["rating"].min()),
                "~",
                float(self.df["rating"].max()),
            )

    def feature_engineering(self) -> None:
        """
        Create derived features and TF-IDF summaries.

        This step:
        - Adds length-based features (char length, word length)
        - Adds time-based features (weekday, year_month)
        - Fits TF-IDF vectorizer and stores numeric summaries per row

        Notes
        -----
        The full TF-IDF matrix is not saved into CSV.
        Instead, this method adds CSV-friendly features:
        - tfidf_nonzero_cnt: number of non-zero TF-IDF terms per review
        - tfidf_sum: sum of TF-IDF weights per review
        """
        # 1) Length features
        self.df["review_char_len"] = self.df["cleaned_content"].astype(str).apply(len)
        self.df["review_word_len"] = self.df["cleaned_content"].astype(str).apply(
            lambda x: len(x.split())
        )

        # 2) Optional trimming for extreme text lengths (tune if needed)
        self.df = self.df[
            (self.df["review_word_len"] >= 2) & (self.df["review_char_len"] <= 3000)
        ]

        # 3) Time features
        day_map = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
        self.df["weekday"] = self.df["date"].dt.dayofweek.map(day_map)
        self.df["year_month"] = self.df["date"].dt.to_period("M").astype(str)

        # 4) TF-IDF
        print("[FE] Fitting TF-IDF...")
        vec = TfidfVectorizer(max_features=1000, min_df=2)
        mat = vec.fit_transform(self.df["cleaned_content"])
        self._tfidf = vec

        self.df["tfidf_nonzero_cnt"] = (mat > 0).sum(axis=1).A1
        self.df["tfidf_sum"] = mat.sum(axis=1).A1

        print(f"[FE] TF-IDF matrix shape: {mat.shape}")
        print(f"[FE] Rows after FE: {len(self.df)}")

    def save_to_database(self) -> None:
        """
        Save the preprocessed Kyobo review dataset to the output directory.

        Output
        ------
        A CSV file named:
            preprocessed_reviews_kyobo.csv
        will be written under:
            {output_dir}
        """
        assert self.df is not None

        os.makedirs(self.output_dir, exist_ok=True)

        save_path = os.path.join(self.output_dir, "preprocessed_reviews_kyobo.csv")
        self.df.to_csv(save_path, index=False, encoding="utf-8-sig")
        print(f"[Save] Saved: {save_path}")