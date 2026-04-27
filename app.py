import torch

from src.presistance.db import init_db
torch.classes.__path__ = []
import streamlit as st
from src.core import init_sessions_state
from src.ui import (
    load_css,
    render_sidebar,
    render_page,
    render_header,
    render_upload_ui,
    render_document_status_ui,
    document_processing,
    render_chat_section,
)
from src.advanced import render_chunk_config

def main():
    # Init DB + Session State
    init_db()
    init_sessions_state()

    # Load UI
    render_page()
    load_css()
    rag_mode = render_sidebar()
    render_header()

    # Config chunk_size, chunk_overlap, retrieval_k UI
    chunk_size, chunk_overlap, retrieval_k = render_chunk_config()

    # Upload (multi-file)
    uploaded_files = render_upload_ui()

    # Document status
    render_document_status_ui()

    # Document Processing Flow (supports list of files)
    document_processing(uploaded_files, chunk_size, chunk_overlap, retrieval_k, rag_mode)

    # Chat history + ask question (Vector/Hybrid option will be inside)
    render_chat_section()

if __name__ == "__main__":
    main()