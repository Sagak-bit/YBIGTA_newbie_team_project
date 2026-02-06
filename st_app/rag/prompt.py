from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate


RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "당신은 리뷰 데이터 기반 Q&A 챗봇입니다. 제공된 컨텍스트(리뷰 발췌)만을 근거로 답하세요. "
            "근거가 부족하면 부족하다고 말하고 추가 질문을 요청하세요. 간결하고 명확하게 답하세요.",
        ),
        (
            "human",
            "질문: {question}\n\n"
            "리뷰 컨텍스트:\n{context}\n\n"
            "답변을 작성하라.",
        ),
    ]
)
