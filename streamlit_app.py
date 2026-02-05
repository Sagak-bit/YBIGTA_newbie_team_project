import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage

from st_app.graph.build_graph import build_graph
from st_app.utils.state import GraphState


st.set_page_config(page_title="RAG+Agent 챗봇", page_icon="🤖")
st.title("RAG + Agent 챗봇 데모")
st.caption("LangChain + LangGraph 기반 라우팅 챗봇")


@st.cache_resource
def get_graph():
    return build_graph()


def _render_messages(messages):
    for msg in messages:
        if isinstance(msg, HumanMessage):
            with st.chat_message("user"):
                st.markdown(msg.content)
        elif isinstance(msg, AIMessage):
            with st.chat_message("assistant"):
                st.markdown(msg.content)


if "messages" not in st.session_state:
    st.session_state.messages = []

_render_messages(st.session_state.messages)

user_input = st.chat_input("질문을 입력하세요")
if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)

    try:
        with st.spinner("답변 생성 중..."):
            graph = get_graph()
            result = graph.invoke(
                GraphState(user_input=user_input, messages=st.session_state.messages)
            )
    except Exception as exc:
        with st.chat_message("assistant"):
            st.error(f"오류가 발생했습니다: {exc}")
    else:
        answer = result.get("response", "답변을 생성하지 못했습니다.")
        with st.chat_message("assistant"):
            st.markdown(answer)

        st.session_state.messages = result.get("messages", st.session_state.messages)
