from __future__ import annotations

from langgraph.graph import END, StateGraph

from st_app.graph.nodes.chat_node import chat_node
from st_app.graph.nodes.rag_review_node import rag_review_node
from st_app.graph.nodes.subject_info_node import subject_info_node
from st_app.graph.router import route_from_llm
from st_app.utils.state import GraphState


def build_graph():
    graph = StateGraph(GraphState)
    graph.add_node("router", route_from_llm)
    graph.add_node("chat", chat_node)
    graph.add_node("subject_info", subject_info_node)
    graph.add_node("rag_review", rag_review_node)

    graph.set_entry_point("router")

    graph.add_conditional_edges(
        "router",
        lambda state: state.route,
        {
            "chat": "chat",
            "subject_info": "subject_info",
            "rag_review": "rag_review",
        },
    )

    graph.add_edge("subject_info", "chat")
    graph.add_edge("rag_review", "chat")
    graph.add_edge("chat", END)

    return graph.compile()
