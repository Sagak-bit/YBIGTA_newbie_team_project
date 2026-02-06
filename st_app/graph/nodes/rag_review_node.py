from __future__ import annotations

from st_app.rag.llm import get_llm
from st_app.rag.prompt import RAG_PROMPT
from st_app.rag.retriever import retrieve
from st_app.utils.state import GraphState


def _format_context(docs) -> str:
    chunks = []
    for i, doc in enumerate(docs, start=1):
        meta = doc.metadata
        source = meta.get("source_file", "unknown")
        rating = meta.get("rating", "NA")
        date = meta.get("date", "NA")
        chunks.append(f"[{i}] ({source}, rating={rating}, date={date}) {doc.content}")
    return "\n".join(chunks)


def rag_review_node(state: GraphState) -> dict:
    docs = retrieve(state.user_input, k=4)
    if not docs:
        return {
            "draft_response": (
                "리뷰 데이터를 찾지 못했습니다. 먼저 리뷰 CSV를 준비하거나 FAISS 인덱스를 생성해 주세요."
            )
        }
    context = _format_context(docs)
    llm = get_llm()
    response = llm.invoke(RAG_PROMPT.format_messages(question=state.user_input, context=context))
    return {
        "retrieved_docs": docs,
        "draft_response": response.content.strip(),
    }
