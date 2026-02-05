from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from langchain_core.messages import BaseMessage


@dataclass
class GraphState:
    """State carried through the LangGraph."""

    user_input: str
    messages: List[BaseMessage] = field(default_factory=list)
    route: Optional[str] = None
    subject_key: Optional[str] = None
    draft_response: Optional[str] = None
    response: Optional[str] = None
    retrieved_docs: Optional[list] = None
