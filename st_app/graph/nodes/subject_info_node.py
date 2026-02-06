from __future__ import annotations

import json
from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate

from st_app.rag.llm import get_llm
from st_app.utils.state import GraphState


BASE_DIR = Path(__file__).resolve().parents[2]
SUBJECTS_PATH = BASE_DIR / "db" / "subject_information" / "subjects.json"


SUBJECT_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "당신은 리뷰 대상 정보 조회 챗봇입니다. 가능한 대상 목록 중 사용자 요청과 가장 관련 있는 "
            "하나의 key를 고르세요. 해당되는 것이 없으면 none만 출력하세요. 출력은 key 또는 none만.",
        ),
        ("human", "대상 목록:\n{choices}\n\n사용자 입력: {text}"),
    ]
)


def _load_subjects() -> dict:
    if not SUBJECTS_PATH.exists():
        return {}
    return json.loads(SUBJECTS_PATH.read_text(encoding="utf-8"))


def subject_info_node(state: GraphState) -> dict:
    subjects = _load_subjects()
    if not subjects:
        return {"draft_response": "현재 등록된 리뷰 대상 정보가 없습니다."}

    llm = get_llm()
    choices = "\n".join([f"- {key}: {val.get('title', '')}" for key, val in subjects.items()])
    response = llm.invoke(SUBJECT_PROMPT.format_messages(text=state.user_input, choices=choices))
    key = response.content.strip()
    if key not in subjects:
        return {"draft_response": "어떤 대상의 정보를 원하시는지 알려주세요."}

    info = subjects[key]
    lines = [
        f"제목: {info.get('title', key)}",
        f"저자: {info.get('author', '정보 없음')}",
        f"요약: {info.get('summary', '정보 없음')}",
    ]
    if info.get("keywords"):
        lines.append(f"키워드: {', '.join(info['keywords'])}")

    return {
        "subject_key": key,
        "draft_response": "\n".join(lines),
    }
