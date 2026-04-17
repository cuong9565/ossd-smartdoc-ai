import torch
torch.classes.__path__ = []
import streamlit as st
from src.core import init_sessions_state
from src.ui import load_css, render_sidebar, render_page, render_header, render_upload_ui, render_document_status_ui, document_processing, render_chat_section
from src.advanced import render_chunk_config
from src.ui import render_benchmark_section

def main():
    # Init Session State
    init_sessions_state()

    # Load UI
    render_page()
    load_css()
    render_sidebar()
    render_header()

    # Config chung_size, chunk_overlap, retieval_k UI
    chunk_size, chunk_overlap, retrieval_k = render_chunk_config()
    st.session_state.retrieval_k = retrieval_k
    # UI Upload File
    uploaded_file = render_upload_ui()

    # UI document status
    render_document_status_ui()

    # Document Processing Flow
    document_processing(uploaded_file, chunk_size, chunk_overlap, retrieval_k)

    # UI chat history && chat question
    render_chat_section()

    # UI benchmark section
    render_benchmark_section()

if __name__ == "__main__":
    main()