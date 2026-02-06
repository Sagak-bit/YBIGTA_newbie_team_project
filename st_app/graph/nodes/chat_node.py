from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate

from st_app.rag.llm import get_llm
from st_app.utils.state import GraphState


CHAT_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "당신은 친절한 대화형 챗봇입니다. 사용자의 질문에 간결하고 명확하게 답하세요. "
            "필요하면 추가 질문으로 정보를 보완하세요.",
        ),
        ("placeholder", "{messages}"),
    ]
)


FINALIZER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "당신은 답변 정리 전문가입니다. 초안을 간결하고 자연스럽게 다듬어 최종 답변으로 정리하세요. "
            "새로운 내용을 추가하지 마세요.",
        ),
        ("human", "초안:\n{draft}\n\n정리된 답변을 작성하라."),
    ]
)


def chat_node(state: GraphState) -> dict:
    llm = get_llm()
    if state.draft_response:
        response = llm.invoke(FINALIZER_PROMPT.format_messages(draft=state.draft_response))
        answer = response.content.strip()
    else:
        messages = state.messages + [HumanMessage(content=state.user_input)]
        response = llm.invoke(CHAT_PROMPT.format_messages(messages=messages))
        answer = response.content.strip()

    return {
        "response": answer,
        "messages": state.messages + [HumanMessage(content=state.user_input), AIMessage(content=answer)],
    }
