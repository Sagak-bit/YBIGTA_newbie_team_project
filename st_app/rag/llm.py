from __future__ import annotations

import os

from langchain_upstage import ChatUpstage, UpstageEmbeddings


def _get_api_key() -> str:
    api_key = os.getenv("UPSTAGE_API_KEY")
    if not api_key:
        try:
            import streamlit as st

            api_key = st.secrets.get("UPSTAGE_API_KEY")
        except Exception:
            api_key = None
    if not api_key:
        raise ValueError(
            "UPSTAGE_API_KEY is missing. Set it as an environment variable or in "
            "Streamlit secrets before running."
        )
    return api_key


def get_llm() -> ChatUpstage:
    api_key = _get_api_key()
    model = os.getenv("UPSTAGE_CHAT_MODEL", "solar-1-mini-chat")
    return ChatUpstage(api_key=api_key, model=model, temperature=0.3)


def get_embeddings() -> UpstageEmbeddings:
    api_key = _get_api_key()
    model = os.getenv("UPSTAGE_EMBEDDING_MODEL", "solar-embedding-1-large")
    return UpstageEmbeddings(api_key=api_key, model=model)
