import torch
torch.classes.__path__ = []
import streamlit as st
from src.core import init_sessions_state
from src.ui import load_css, render_sidebar, render_page, render_header
from src.ui.multi_document_processing import render_multi_document_processing
from src.ui.multi_document_chat import render_multi_document_chat

def main():
    # Init Session State
    init_sessions_state()

    # Load UI
    render_page()
    load_css()
    render_sidebar()
    render_header()

    # Multi-document processing (upload nhiều file + chunking + metadata)
    render_multi_document_processing()

    # Multi-document chat (filter metadata + hỏi đáp + hiển thị nguồn)
    render_multi_document_chat()

if __name__ == "__main__":
    main()