import streamlit as st

def init_sessions_state():
    # Lưu danh sách cuộc hội thoại
    # Mỗi một chat_history_ui có cấu trúc sau
        # "role": "user" || "",
        # "content": "CÂU HỎI CỦA BẠN" || "PHẢN HỒI CỦA AI",
        # "timestamp": Thời điểm phản hồi,
        # "response_time": Thời gian phản hồi || None
        # "sources": Danh sách nội dung liên quan || None
        # "keywords": Danh sách keywords liên quan || None
    if "chat_history_ui" not in st.session_state:
        st.session_state.chat_history_ui = []
    
    # Lưu true hoặc false là có sử dụng rag_mode không
    if "rag_mode" not in st.session_state:
        st.session_state.rag_mode = "RAG"
    
    # Lưu true hoặc false là có sử dụng graph_rag_mode không
    if "graph_rag_mode" not in st.session_state:
        st.session_state.graph_rag_mode = False

    if "graph_triples" not in st.session_state:
        st.session_state.graph_triples = []

    if "last_dual_responses" not in st.session_state:
        st.session_state.last_dual_responses = None

    if "retriever" not in st.session_state:
        st.session_state.retriever = None

    if "vector_db" not in st.session_state:
        st.session_state.vector_db = None

    if "uploaded_file_name" not in st.session_state:
        st.session_state.uploaded_file_name = None

    if "document_chunks" not in st.session_state:
        st.session_state.document_chunks = 0
        
    if "documents" not in st.session_state:
      st.session_state.documents = None
    
    if "retrieval_k" not in st.session_state:
      st.session_state.retrieval_k = None
    