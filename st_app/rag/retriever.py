from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List

import pandas as pd
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from st_app.rag.llm import get_embeddings


BASE_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BASE_DIR.parent
FAISS_DIR = BASE_DIR / "db" / "faiss_index"
META_PATH = FAISS_DIR / "meta.json"
INDEX_PATH = FAISS_DIR / "index.faiss"
INDEX_META_PATH = FAISS_DIR / "index.pkl"


@dataclass
class RetrievedDoc:
    content: str
    metadata: dict
    score: float


def _load_reviews(max_rows: int = 500) -> List[Document]:
    candidates = [
        PROJECT_ROOT / "database" / "preprocessed_reviews_kyobo.csv",
        PROJECT_ROOT / "database" / "preprocessed_reviews_aladin.csv",
        PROJECT_ROOT / "database" / "preprocessed_reviews_yes24.csv",
    ]
    docs: List[Document] = []
    for path in candidates:
        if not path.exists():
            continue
        df = pd.read_csv(path)
        if "cleaned_content" in df.columns:
            text_col = "cleaned_content"
        else:
            text_col = "content"
        use_df = df.dropna(subset=[text_col]).head(max_rows)
        for _, row in use_df.iterrows():
            content = str(row[text_col]).strip()
            if not content:
                continue
            metadata = {
                "source_file": path.name,
                "rating": float(row["rating"]) if "rating" in row else None,
                "date": str(row["date"]) if "date" in row else None,
            }
            docs.append(Document(page_content=content, metadata=metadata))
    return docs


def _save_meta(count: int) -> None:
    FAISS_DIR.mkdir(parents=True, exist_ok=True)
    meta = {
        "doc_count": count,
        "built_from": "database/preprocessed_reviews_*.csv",
    }
    META_PATH.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def _build_index() -> FAISS:
    docs = _load_reviews()
    if not docs:
        raise FileNotFoundError(
            "No review CSVs found. Expected files under database/."
        )
    embeddings = get_embeddings()
    vectorstore = FAISS.from_documents(docs, embeddings)
    FAISS_DIR.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(FAISS_DIR))
    _save_meta(len(docs))
    return vectorstore


def get_vectorstore() -> FAISS:
    if _has_valid_index():
        embeddings = get_embeddings()
        return FAISS.load_local(
            str(FAISS_DIR),
            embeddings,
            allow_dangerous_deserialization=True,
        )
    return _build_index()


def _has_valid_index() -> bool:
    if not FAISS_DIR.exists():
        return False
    if not INDEX_PATH.exists() or not INDEX_META_PATH.exists():
        return False
    if INDEX_PATH.stat().st_size == 0 or INDEX_META_PATH.stat().st_size == 0:
        return False
    return True


def retrieve(query: str, k: int = 4) -> List[RetrievedDoc]:
    try:
        vectorstore = get_vectorstore()
    except FileNotFoundError:
        return []
    results = vectorstore.similarity_search_with_score(query, k=k)
    retrieved: List[RetrievedDoc] = []
    for doc, score in results:
        retrieved.append(RetrievedDoc(content=doc.page_content, metadata=doc.metadata, score=score))
    return retrieved
