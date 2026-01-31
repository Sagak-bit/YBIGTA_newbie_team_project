# database/seed_reviews_to_mongo.py
from __future__ import annotations

import hashlib
import os
from typing import Iterable, Dict, Any

import pandas as pd
from pymongo.collection import Collection
from pymongo import UpdateOne
from dotenv import load_dotenv

from database.mongodb_connection import mongo_db  # 당신이 연결 확인한 mongo_db

load_dotenv()

DATA_DIR = os.path.join(os.path.dirname(__file__))  # database/
RAW_FILES = {
    "kyobo": os.path.join(DATA_DIR, "reviews_kyobo.csv"),
    "yes24": os.path.join(DATA_DIR, "reviews_yes24.csv"),
    "aladin": os.path.join(DATA_DIR, "reviews_aladin.csv"),
}

def make_row_id(site: str, date: str, rating: str, content: str) -> str:
    key = f"{site}||{date}||{rating}||{content}".encode("utf-8", errors="ignore")
    return hashlib.sha256(key).hexdigest()

def upsert_many(col: Collection, docs: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    ops = []
    for d in docs:
        _id = d["_id"]
        ops.append(UpdateOne({"_id": _id}, {"$setOnInsert": d}, upsert=True))

    if not ops:
        return {"matched": 0, "inserted": 0, "modified": 0}

    res = col.bulk_write(ops, ordered=False)
    # upserted_count는 "새로 들어간 수"를 의미
    return {
        "matched": res.matched_count,
        "inserted": res.upserted_count,
        "modified": res.modified_count,
    }

def load_csv(path: str) -> pd.DataFrame:
    # 인코딩 방어
    for enc in ("utf-8-sig", "utf-8"):
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path)

def seed_site(site: str, csv_path: str) -> None:
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    df = load_csv(csv_path)

    required = {"rating", "date", "content"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"[{site}] Missing required columns: {sorted(missing)}")

    # 문자열화(해시 안정성)
    df["rating"] = df["rating"].astype(str)
    df["date"] = df["date"].astype(str)
    df["content"] = df["content"].astype(str)

    docs = []
    for row in df.to_dict("records"):
        _id = make_row_id(site, row["date"], row["rating"], row["content"])
        docs.append({
            "_id": _id,
            "site": site,
            "rating": row["rating"],
            "date": row["date"],
            "content": row["content"],
        })

    col_name = f"reviews_{site}"
    col = mongo_db[col_name]
    # _id 자체가 unique라 별도 index 없어도 중복 방지됨(그래도 조회용 인덱스 추가 가능)
    col.create_index("site")
    col.create_index("date")

    stats = upsert_many(col, docs)
    print(f"[seed] {col_name}: total={len(docs)} inserted={stats['inserted']} matched={stats['matched']}")

def main() -> None:
    for site, path in RAW_FILES.items():
        seed_site(site, path)

if __name__ == "__main__":
    main()
