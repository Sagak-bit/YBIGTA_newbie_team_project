from __future__ import annotations

import os
import re
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Optional, Any, Set

# scikit-learn이 설치되어 있어야 합니다.
from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore
from review_analysis.preprocessing.base_processor import BaseDataProcessor

class Yes24Processor(BaseDataProcessor):
    def __init__(self, input_path: str, output_dir: str) -> None:
        """
        :param input_path: 크롤링된 reviews_yes24.csv 경로
        :param output_dir: 전처리된 파일이 저장될 database 폴더 경로
        """
        super().__init__(input_path, output_dir)
        self.df_pre: Optional[pd.DataFrame] = None
        self.df_fe: Optional[pd.DataFrame] = None

    def preprocess(self) -> None:
        """
        2) preprocess() 단계
        - CSV 읽기
        - 결측 제거, 타입 변환
        - 이상치 제거 (별점, 미래 날짜)
        - 텍스트 정제 및 길이 필터링 (초단문 + 초장문 제거)
        """
        print("[Yes24Processor] Preprocessing started...")

        # 2.1 CSV 읽기
        try:
            df = pd.read_csv(self.input_path, encoding='utf-8-sig')
        except UnicodeDecodeError:
            df = pd.read_csv(self.input_path, encoding='utf-8')
        
        original_len = len(df)

        # 2.2 결측 제거
        df = df.dropna(subset=['rating', 'date', 'content'])

        # 2.3 타입 정리
        df['rating'] = pd.to_numeric(df['rating'], errors='coerce')
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        # 변환 실패(NaN, NaT) 행 제거
        df = df.dropna(subset=['rating', 'date'])

        # 2.4 데이터 값 이상치 제거
        # 별점 [1, 5] 범위
        df = df[(df['rating'] >= 1) & (df['rating'] <= 5)]
        
        # 미래 날짜 제거
        today = pd.Timestamp(datetime.now().date())
        df = df[df['date'] <= today]

        # 2.5 텍스트 정제
        def clean_text(text: Any) -> str:
            s_text = str(text)
            # 한글, 영문, 숫자, 기본 문장부호만 허용
            s_text = re.sub(r'[^0-9a-zA-Z가-힣\s.,!?…]', ' ', s_text)
            # 연속 공백 정리
            s_text = re.sub(r'\s+', ' ', s_text).strip()
            return s_text

        df['content_clean'] = df['content'].apply(clean_text)
        df['content_len'] = df['content_clean'].apply(len)

        # 2.6 길이 이상치 제거 (Length Outliers)
        # (1) 초단문 제거: 5글자 미만
        df = df[df['content_len'] >= 5]
        
        # (2) 초장문 제거: 상위 1% (99th Percentile) 이상 제거
        upper_limit = df['content_len'].quantile(0.99)
        df = df[df['content_len'] <= upper_limit]
        
        print(f"[Yes24Processor] Rows filtered: {original_len} -> {len(df)} (Upper limit: {upper_limit:.0f} chars)")
        
        self.df_pre = df.reset_index(drop=True)

    def feature_engineering(self) -> None:
        """
        3) feature_engineering() 단계
        - 날짜 파생변수 생성
        - 불용어 처리
        - TF-IDF 벡터화 (max_features=1000, min_df=2)
        """
        if self.df_pre is None:
            raise ValueError("Run preprocess() first.")
        
        print("[Yes24Processor] Feature Engineering started...")
        df = self.df_pre.copy()

        # 3.1 날짜 파생변수 생성
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month
        df['weekday'] = df['date'].dt.weekday  # 월=0 ~ 일=6
        df['is_weekend'] = df['weekday'].apply(lambda x: 1 if x >= 5 else 0)
        df['year_month'] = df['date'].dt.strftime('%Y-%m')

        # 3.2 텍스트 벡터화 (TF-IDF)
        
        STOPWORDS: Set[str] = {"책", "구매", "배송", "포장", "진짜", "너무", "좋아요"}

        def simple_tokenizer(text: str) -> List[str]:
            tokens = text.split()
            # [NEW] 길이 2 이상이면서 & 불용어가 아닌 단어만 추출
            return [t for t in tokens if len(t) >= 2 and t not in STOPWORDS]

        vectorizer = TfidfVectorizer(
            tokenizer=simple_tokenizer,
            token_pattern=None,
            # [NEW] 기획서 2.5 반영
            max_features=1000,  # 상위 1000개 단어
            min_df=2,           # 최소 2번 이상 등장한 단어만
            ngram_range=(1, 2)  # Unigram + Bigram
        )

        # 벡터화 수행
        tfidf_matrix = vectorizer.fit_transform(df['content_clean'])
        
        # DataFrame 변환 (컬럼명: tfidf__단어)
        feature_names = vectorizer.get_feature_names_out()
        tfidf_cols = [f"tfidf__{name}" for name in feature_names]
        
        dense_matrix = tfidf_matrix.toarray()
        df_tfidf = pd.DataFrame(dense_matrix, columns=tfidf_cols, index=df.index)

        # 해당 리뷰의 정보량(키워드 중요도 합계)을 나타냄
        df['tfidf_sum'] = df_tfidf.sum(axis=1)

        # 기존 df와 결합
        self.df_fe = pd.concat([df, df_tfidf], axis=1)
        
        if self.df_fe is not None:
             print(f"[Yes24Processor] FE done. Total columns: {self.df_fe.shape[1]}")

    def save_to_database(self) -> None:
        """
        4) 결과 저장
        """
        if self.df_fe is None:
            raise ValueError("Run feature_engineering() first.")

        os.makedirs(self.output_dir, exist_ok=True)
        output_path = os.path.join(self.output_dir, "preprocessed_reviews_yes24.csv")
        
        self.df_fe.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"[Yes24Processor] Saved to {output_path}")

if __name__ == "__main__":
    # 테스트 실행용 코드
    processor = Yes24Processor(
        input_path="database/reviews_yes24.csv", 
        output_dir="database"
    )
    
    if os.path.exists("database/reviews_yes24.csv"):
        processor.preprocess()
        processor.feature_engineering()
        processor.save_to_database()
    else:
        print("테스트용 csv 파일이 없습니다.")