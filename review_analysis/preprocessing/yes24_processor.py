from __future__ import annotations

import os
import re
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Optional, Any, cast

from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore
from review_analysis.preprocessing.base_processor import BaseDataProcessor

class Yes24Processor(BaseDataProcessor):
    def __init__(self, input_path: str, output_dir: str) -> None:
        """
        :param input_path: 크롤링된 reviews_yes24.csv 경로
        :param output_dir: 전처리된 파일이 저장될 database 폴더 경로
        """
        super().__init__(input_path, output_dir)
        # 초기 상태는 None이므로 Optional[pd.DataFrame]으로 선언
        self.df_pre: Optional[pd.DataFrame] = None
        self.df_fe: Optional[pd.DataFrame] = None

    def preprocess(self) -> None:
        """
        2) preprocess() 단계
        - CSV 읽기 (utf-8-sig / utf-8)
        - 결측 제거, 타입 변환
        - 이상치(별점, 미래 날짜) 제거
        - 텍스트 정제(content_clean) 및 길이 필터링
        """
        print("[Yes24Processor] Preprocessing started...")

        # 2.1 CSV 읽기
        try:
            df = pd.read_csv(self.input_path, encoding='utf-8-sig')
        except UnicodeDecodeError:
            df = pd.read_csv(self.input_path, encoding='utf-8')
        
        # 2.2 결측 제거 (rating, date, content 중 하나라도 없으면 삭제)
        original_len = len(df)
        df = df.dropna(subset=['rating', 'date', 'content'])

        # 2.3 타입 정리
        # rating: 숫자로 변환 (실패 시 NaN -> 이후 삭제)
        df['rating'] = pd.to_numeric(df['rating'], errors='coerce')
        # date: 날짜로 변환 (실패 시 NaT -> 이후 삭제)
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        # 변환 후 다시 NaN/NaT 제거
        df = df.dropna(subset=['rating', 'date'])

        # 2.4 이상치 제거
        # 별점 범위 [1, 5] 벗어나면 삭제 (타입 추론을 위해 float 변환 가정)
        df = df[(df['rating'] >= 1) & (df['rating'] <= 5)]
        
        # 미래 날짜 제거 (방어 로직)
        today = pd.Timestamp(datetime.now().date())
        df = df[df['date'] <= today]

        # 2.5 텍스트 정제 + 길이 계산
        # 팀원 규칙: 한글/영문/숫자/공백/기본 문장부호(.,!?…) 만 허용
        def clean_text(text: Any) -> str:
            s_text = str(text)
            # 허용 문자 외에는 공백으로 치환
            s_text = re.sub(r'[^0-9a-zA-Z가-힣\s.,!?…]', ' ', s_text)
            # 연속 공백 1개로 줄이고 strip
            s_text = re.sub(r'\s+', ' ', s_text).strip()
            return s_text

        # apply 적용 시 반환 타입 명확화를 위해 할당
        df['content_clean'] = df['content'].apply(clean_text)
        df['content_len'] = df['content_clean'].apply(len)

        # 2.6 너무 짧은 리뷰 제거 (5글자 미만)
        df = df[df['content_len'] >= 5]
        
        print(f"[Yes24Processor] Rows filtered: {original_len} -> {len(df)}")
        
        # 인덱스 재설정 후 인스턴스 변수에 저장
        self.df_pre = df.reset_index(drop=True)

    def feature_engineering(self) -> None:
        """
        3) feature_engineering() 단계
        - 날짜 파생변수 생성 (year, month, weekday, is_weekend, year_month)
        - TF-IDF 벡터화 (max_features=200, ngram=(1,2))
        """
        if self.df_pre is None:
            raise ValueError("Run preprocess() first.")
        
        print("[Yes24Processor] Feature Engineering started...")
        # mypy가 self.df_pre를 None으로 인식하지 않도록 복사본 생성
        df = self.df_pre.copy()

        # 3.1 날짜 파생변수 생성
        # df['date']는 datetime64[ns] 타입이어야 함 (.dt 접근자 사용)
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month
        df['weekday'] = df['date'].dt.weekday  # 월=0, ... 일=6
        
        # apply lambda에 대한 타입 힌트가 어려울 수 있으므로 함수로 분리하거나 직접 적용
        # 여기서는 int로 캐스팅하여 저장
        df['is_weekend'] = df['weekday'].apply(lambda x: 1 if x >= 5 else 0)
        df['year_month'] = df['date'].dt.strftime('%Y-%m')

        # 3.2 텍스트 임베딩 (TF-IDF)
        def simple_tokenizer(text: str) -> List[str]:
            tokens = text.split()
            return [t for t in tokens if len(t) >= 2]

        vectorizer = TfidfVectorizer(
            tokenizer=simple_tokenizer,
            token_pattern=None,  # tokenizer 파라미터를 쓰므로 None 처리
            max_features=200,    # 팀원 설정: 최대 200개
            ngram_range=(1, 2)   # 팀원 설정: unigram + bigram
        )

        # content_clean 컬럼을 사용하여 벡터화
        # fit_transform은 sparse matrix를 반환
        tfidf_matrix = vectorizer.fit_transform(df['content_clean'])
        
        # 벡터 결과를 DataFrame으로 변환 (컬럼명: tfidf__{단어})
        feature_names = vectorizer.get_feature_names_out()
        tfidf_cols = [f"tfidf__{name}" for name in feature_names]
        
        # toarray() 호출
        dense_matrix = tfidf_matrix.toarray()
        
        df_tfidf = pd.DataFrame(dense_matrix, columns=tfidf_cols, index=df.index)

        # 기존 df와 결합
        self.df_fe = pd.concat([df, df_tfidf], axis=1)
        
        if self.df_fe is not None:
             print(f"[Yes24Processor] FE done. Total columns: {self.df_fe.shape[1]}")

    def save_to_database(self) -> None:
        """
        4) 결과 저장
        - output_dir에 preprocessed_reviews_yes24.csv 로 저장
        """
        if self.df_fe is None:
            raise ValueError("Run feature_engineering() first.")

        os.makedirs(self.output_dir, exist_ok=True)
        output_path = os.path.join(self.output_dir, "preprocessed_reviews_yes24.csv")
        
        # 팀원 포맷에 맞춰 utf-8-sig 저장 (엑셀 호환)
        self.df_fe.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"[Yes24Processor] Saved to {output_path}")

if __name__ == "__main__":
    # 경로 설정 (테스트용)
    processor = Yes24Processor(
        input_path="database/reviews_yes24.csv", 
        output_dir="database"
    )
    # 실제 파일이 없으면 에러가 나므로 예외처리 혹은 주석 처리 후 사용
    if os.path.exists("database/reviews_yes24.csv"):
        processor.preprocess()
        processor.feature_engineering()
        processor.save_to_database()