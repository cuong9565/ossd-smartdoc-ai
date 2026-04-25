import streamlit as st

def init_sessions_state():
    # Khởi tạo chat_history_ui (danh sách cuộc hội thoại)
    # Cấu trúc mỗi message:
    #     role: "user" | "ai"
    #     content: nội dung câu hỏi/phản hồi
    #     timestamp: thời điểm
    #     response_time: thời gian phản hồi
    #     sources: danh sách nội dung liên quan
    #     keywords: từ khóa liên quan
    #     mode: "RAG" | "Graph RAG"
    if "chat_history_ui" not in st.session_state:
        st.session_state.chat_history_ui = []
    
    # "RAG" | "Graph RAG" | "RAG, Graph RAG"
    if "rag_mode" not in st.session_state:
        st.session_state.rag_mode = "RAG"
    
    # danh sách triples từ knowledge graph
    if "graph_triples" not in st.session_state:
        st.session_state.graph_triples = []

    # vector retriever
    if "last_dual_responses" not in st.session_state:
        st.session_state.last_dual_responses = None

    # vector retriever
    if "retriever" not in st.session_state:
        st.session_state.retriever = None

    # FAISS database
    if "vector_db" not in st.session_state:
        st.session_state.vector_db = None

    # tên file đã upload
    if "uploaded_file_name" not in st.session_state:
        st.session_state.uploaded_file_name = None

    # số lượng chunks
    if "document_chunks" not in st.session_state:
        st.session_state.document_chunks = 0
        
    # danh sách documents
    if "documents" not in st.session_state:
      st.session_state.documents = None
    
    # số lượng documents truy xuất
    if "retrieval_k" not in st.session_state:
      st.session_state.retrieval_k = None
    