from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

from st_app.rag.llm import get_llm
from st_app.utils.state import GraphState


ROUTER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a router that classifies user requests. Output exactly one label.\n"
            "- chat: general conversation, greetings, small talk\n"
            "- subject_info: request for basic subject information (book/product)\n"
            "- rag_review: request for review-based information (summary, opinions, pros/cons)\n"
            "If unsure, output chat. Output only the label.",
        ),
        ("human", "User input: {text}"),
    ]
)


def route_from_llm(state: GraphState) -> dict:
    llm = get_llm()
    response = llm.invoke(ROUTER_PROMPT.format_messages(text=state.user_input))
    label = response.content.strip().lower()
    if label not in {"chat", "subject_info", "rag_review"}:
        label = "chat"
    return {"route": label}
