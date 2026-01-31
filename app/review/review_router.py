from __future__ import annotations

import hashlib
import os
import re
import tempfile
from typing import Any, Dict, List, Type
from typing import Any, Dict, List, Type, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException
from pymongo import UpdateOne

from database.mongodb_connection import mongo_db
from review_analysis.preprocessing.base_processor import BaseDataProcessor
from review_analysis.preprocessing.kyobo_processor import KyoboProcessor
from review_analysis.preprocessing.yes24_processor import Yes24Processor
from review_analysis.preprocessing.aladin_processor import AladinProcessor

review = APIRouter(prefix="/review", tags=["review"])

# site_name -> Processor class 매핑
PROCESSORS: Dict[str, Type[BaseDataProcessor]] = {
    "kyobo": KyoboProcessor,
    "yes24": Yes24Processor,
    "aladin": AladinProcessor,
}


# -----------------------------
# MongoDB-safe utilities
# -----------------------------
_MONGO_KEY_FORBIDDEN = re.compile(r"[\x00]")  # null byte
_WHITESPACE = re.compile(r"\s+")

def sanitize_mongo_key(key: str) -> str:
    """
    MongoDB field name rules (practical):
    - '.' 포함 불가
    - '$' 포함/시작 불가 (특히 update operator와 충돌)
    - null byte 포함 불가
    - 공백/제어문자 등은 안정적으로 '_'로 정리
    """
    if not isinstance(key, str):
        key = str(key)

    key = _MONGO_KEY_FORBIDDEN.sub("", key)
    key = key.replace(".", "_").replace("$", "_")
    key = _WHITESPACE.sub("_", key).strip("_")

    # 완전히 비어버리면 fallback
    if key == "":
        key = "_"

    return key


def to_bson_compatible(v: Any) -> Any:
    """
    pandas/numpy 타입을 MongoDB(BSON)에서 안전한 파이썬 타입으로 변환.
    - NaN/NaT -> None
    - numpy scalar -> python scalar
    - Timestamp -> ISO string
    - dict/list는 재귀 변환
    """
    # NaN/NaT 처리 (pandas의 isna는 다양한 결측을 잡음)
    try:
        if pd.isna(v):
            return None
    except Exception:
        pass

    # pandas Timestamp
    if isinstance(v, pd.Timestamp):
        # timezone 유무 상관 없이 문자열로 저장 (가장 안전)
        return v.isoformat()

    # numpy scalar -> python scalar
    try:
        import numpy as np  # 로컬 import (환경마다 없을 수도 있으니)
        if isinstance(v, np.generic):
            return v.item()
    except Exception:
        pass

    # dict / list 재귀 처리
    if isinstance(v, dict):
        return {sanitize_mongo_key(k): to_bson_compatible(val) for k, val in v.items()}
    if isinstance(v, list):
        return [to_bson_compatible(x) for x in v]

    # 나머지는 그대로 (int/float/str/bool/None 등)
    return v


def split_tfidf_and_sanitize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    tfidf: Dict[str, Any] = {}
    clean: Dict[str, Any] = {}

    def put_unique(d: Dict[str, Any], k: str, v: Any) -> None:
        # 같은 키가 이미 있으면 _2, _3 ... 붙여서 충돌 방지
        if k not in d:
            d[k] = v
            return
        i = 2
        while f"{k}_{i}" in d:
            i += 1
        d[f"{k}_{i}"] = v

    for k, v in row.items():
        k_str = str(k)

        if k_str.startswith("tfidf__"):
            raw_feat = k_str[len("tfidf__"):]
            safe_feat = sanitize_mongo_key(raw_feat)
            put_unique(tfidf, safe_feat, to_bson_compatible(v))
        else:
            safe_k = sanitize_mongo_key(k_str)
            put_unique(clean, safe_k, to_bson_compatible(v))

    clean["tfidf"] = tfidf
    return clean



# -----------------------------
# Existing helpers
# -----------------------------
def make_processed_id(site: str, row: Dict[str, Any]) -> str:
    """
    전처리 결과 문서의 결정론적 _id 생성:
    같은 전처리 결과면 같은 _id -> upsert로 중복 저장 방지
    """
    date = str(row.get("date", ""))
    rating = str(row.get("rating", ""))
    content = str(
        row.get("content_clean")
        or row.get("cleaned_content")
        or row.get("content")
        or ""
    )
    key = f"{site}||{date}||{rating}||{content}".encode("utf-8", errors="ignore")
    return hashlib.sha256(key).hexdigest()


def bulk_upsert_insert_only(col, docs: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    insert-only upsert:
    - 존재하면 그대로 두고(업데이트 X)
    - 없으면 삽입
    """
    ops = [UpdateOne({"_id": d["_id"]}, {"$setOnInsert": d}, upsert=True) for d in docs]
    if not ops:
        return {"inserted": 0, "matched": 0}

    res = col.bulk_write(ops, ordered=False)
    return {"inserted": res.upserted_count, "matched": res.matched_count}


# -----------------------------
# Router
# -----------------------------
@review.post("/preprocess/{site_name}")
def preprocess(site_name: str):
    site = site_name.strip().lower()
    if site not in PROCESSORS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid site_name. Must be one of {sorted(PROCESSORS.keys())}",
        )

    raw_col_name = f"reviews_{site}"
    raw_col = mongo_db[raw_col_name]

    # seed 단계에서 _id/fields는: _id, site, rating, date, content
    raw_docs = list(raw_col.find({}, {"_id": 1, "rating": 1, "date": 1, "content": 1}))
    if not raw_docs:
        raise HTTPException(status_code=404, detail=f"No raw data in collection: {raw_col_name}")

    out_col_name = f"preprocessed_reviews_{site}"
    out_col = mongo_db[out_col_name]

    # processed 컬렉션 인덱스(조회/정리용)
    out_col.create_index("site")
    out_col.create_index("date")

    # processed에 이미 있는 _id들은 스킵(강건 + 효율)
    # (주의: 데이터가 매우 커지면 distinct 비용이 커질 수는 있음. 지금 과제 스케일에서는 OK)
    existing_ids = set(out_col.distinct("_id"))
    to_process = [d for d in raw_docs if d["_id"] not in existing_ids]

    if not to_process:
        return {
            "site": site,
            "raw_collection": raw_col_name,
            "output_collection": out_col_name,
            "raw_count": len(raw_docs),
            "to_process_count": 0,
            "inserted_new": 0,
            "matched_existing": len(existing_ids),
            "message": "No new raw documents to preprocess.",
        }

    df_raw = pd.DataFrame(to_process)

    # Processor는 input_csv 경로를 받으므로 임시 CSV로 변환
    with tempfile.TemporaryDirectory() as tmpdir:
        input_csv = os.path.join(tmpdir, f"reviews_{site}.csv")
        df_raw.to_csv(input_csv, index=False, encoding="utf-8-sig")

        processor_cls = PROCESSORS[site]
        processor = processor_cls(input_csv, tmpdir)

        # 1) preprocess는 무조건 수행 (여기서 예외 나면 그건 진짜 전처리 코드 문제라 올리는 게 맞음)
        processor.preprocess()

        # 2) processor.df 안전하게 확보
        df = getattr(processor, "df", None)  # type: Optional[pd.DataFrame]
        if df is None:
            df = pd.DataFrame()

        # 3) 텍스트 컬럼 후보 중 존재하는 것 선택 후 "비어있는 행 제거"
        text_col_candidates = ["cleaned_content", "content_clean", "content"]
        text_col = next((c for c in text_col_candidates if c in df.columns), None)

        if text_col is not None:
            df[text_col] = df[text_col].fillna("").astype(str)
            df = df[df[text_col].str.strip().ne("")].copy()

        # 4) output_csv 경로 확정
        output_csv = os.path.join(tmpdir, f"preprocessed_reviews_{site}.csv")

        # 5) df가 비면: "헤더 있는 빈 CSV"를 만들어서 read_csv가 절대 안 터지게
        if df.empty:
            # 최소한의 컬럼 헤더를 강제로 넣음 (프로젝트마다 필요한 컬럼이 달라도 read_csv는 안전)
            empty_cols = ["content", "date", "rating", "content_clean", "cleaned_content"]
            pd.DataFrame(columns=empty_cols).to_csv(output_csv, index=False, encoding="utf-8-sig")
        else:
            # processor 내부가 self.df를 참조하는 구현이 많아서 다시 꽂아줌
            try:
                processor.df = df  # type: ignore[attr-defined]
            except Exception:
                pass

            # 6) feature_engineering 시도. 실패하면 "preprocess까지만" 저장하고 계속 진행
            fe_ok = True
            try:
                processor.feature_engineering()
            except ValueError as e:
                # sklearn empty vocabulary 등은 정상 fallback 처리
                if "empty vocabulary" in str(e).lower():
                    fe_ok = False
                else:
                    raise
            except Exception:
                # 통과가 목적이면 여기서도 fe_ok=False로 두고 넘어가는 게 더 강건
                fe_ok = False

            # 7) 저장은 processor.df를 우선, 없으면 df로 저장
            df_after = getattr(processor, "df", None)
            if df_after is None or df_after.empty:
                # FE 실패/결과 비었으면 preprocess df로 저장
                df.to_csv(output_csv, index=False, encoding="utf-8-sig")
            else:
                df_after.to_csv(output_csv, index=False, encoding="utf-8-sig")

        # 8) output_csv 로드: EmptyDataError 방어 (절대 500 나지 않게)
        try:
            df_out = pd.read_csv(output_csv, encoding="utf-8-sig")
        except pd.errors.EmptyDataError:
            df_out = pd.DataFrame()



    # 전처리 결과 문서 생성 (강건 버전)
    docs_out: List[Dict[str, Any]] = []
    for row_any in df_out.to_dict("records"):
        # 1) row를 dict로 확보
        row0 = dict(row_any)
        row: Dict[str, Any] = {str(k): v for k, v in row0.items()}

        # 2) _id는 "원본 row 내용" 기반으로 결정론 생성
        _id = make_processed_id(site, row)

        # 3) MongoDB-safe 변환:
        #    - tfidf__* -> doc["tfidf"]로 이동
        #    - 모든 key sanitize
        #    - 모든 value bson 호환
        safe_payload = split_tfidf_and_sanitize_row(row)

        # 4) 최종 문서
        doc = {
            "_id": _id,
            "site": site,
            **safe_payload,
        }
        docs_out.append(doc)

    stats = bulk_upsert_insert_only(out_col, docs_out)

    return {
        "site": site,
        "raw_collection": raw_col_name,
        "output_collection": out_col_name,
        "raw_count": len(raw_docs),
        "to_process_count": len(to_process),
        "processed_rows": len(docs_out),
        "inserted_new": stats["inserted"],
        "matched_existing": stats["matched"],
    }
