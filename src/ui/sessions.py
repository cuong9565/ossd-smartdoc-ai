import streamlit as st

def init_sessions_state():
    if "chat_history_ui" not in st.session_state:
        st.session_state.chat_history_ui = []

    if "retriever" not in st.session_state:
        st.session_state.retriever = None

    if "vector_db" not in st.session_state:
        st.session_state.vector_db = None

    if "uploaded_file_name" not in st.session_state:
        st.session_state.uploaded_file_name = None

    if "document_chunks" not in st.session_state:
        st.session_state.document_chunks = 0