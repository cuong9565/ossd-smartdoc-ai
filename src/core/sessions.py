import os
import uuid

from langchain_community.vectorstores import FAISS
import streamlit as st
from .config import Config
from src.presistance.history_manager import load_document_state, load_history, load_retriever_state

def init_sessions_state():
    
    # name: "RAG" | "Graph RAG" | "RAG, Graph RAG"
    # step: []
    if "rag_mode" not in st.session_state:
        st.session_state.rag_mode = {
            "name": None,
            "step": []
        }

    
    # danh sách triples từ knowledge graph
    if "graph_triples" not in st.session_state:
        st.session_state.graph_triples = []

    # vector retriever
    if "last_dual_responses" not in st.session_state:
        st.session_state.last_dual_responses = None

    # FAISS database
    if "vector_db" not in st.session_state:
        st.session_state.vector_db = None

    # Hybrid retriever cache (optional)
    if "hybrid_retriever" not in st.session_state:
        st.session_state.hybrid_retriever = None

    # Toggle rerank (Cross-Encoder) for fair Vector/Hybrid comparison
    if "use_rerank" not in st.session_state:
        st.session_state.use_rerank = False

    # tên file đã upload
    if "uploaded_file_name" not in st.session_state:
        st.session_state.uploaded_file_name = None
        
    # danh sách documents
    if "documents" not in st.session_state:
        st.session_state.documents = []
    
    # số lượng documents truy xuất
    if "retrieval_k" not in st.session_state:
        # Default an toàn để tránh TypeError khi int(None)
        st.session_state.retrieval_k = 4

    # Search mode cho multi-document UI (Vector/Hybrid)
    if "search_mode" not in st.session_state:
        st.session_state.search_mode = "Vector"

    if "document_meta" not in st.session_state:
        st.session_state.document_meta = None

    if "is_processing" not in st.session_state:
        st.session_state.is_processing = False
    
    sid = st.query_params.get("sid")
    if isinstance(sid, list):
        sid = sid[0] if sid else None
    sid = str(sid).strip() if sid else None

    current_session_id = st.session_state.get("session_id")
    if sid and current_session_id != sid:
        st.session_state.session_id = sid
        st.session_state.pop("chat_history_ui", None)
        st.session_state.pop("retriever", None)
        st.session_state.pop("vector_db", None)
        st.session_state.pop("retrieval_k", None)
    elif "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())

    if st.query_params.get("sid") != st.session_state.session_id:
        st.query_params["sid"] = st.session_state.session_id

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
        # Không để lỗi DB làm app crash: fallback về list rỗng
        try:
            st.session_state.chat_history_ui = load_history(st.session_state.session_id) or []
        except Exception:
            st.session_state.chat_history_ui = []

    # vector retriever
    if "retriever" not in st.session_state:
        saved_state = load_retriever_state(st.session_state.session_id)
        if saved_state:
            # DB đang lưu key là retriever_k (không phải retrieval_k)
            st.session_state.retrieval_k = saved_state.get("retriever_k") or 4
            saved_mode = saved_state.get("mode")

            # Mode trong DB có 2 loại:
            # - Rag mode: "RAG" | "Graph RAG" | "RAG, Graph RAG"
            # - Search mode: "Vector" | "Hybrid"
            # Tránh gán nhầm "RAG" vào search_mode (radio chỉ có Vector/Hybrid)
            if saved_mode in {"Vector", "Hybrid"}:
                st.session_state.search_mode = saved_mode

            # Nếu DB đã có mode RAG/GraphRAG thì restore luôn để UI không bắt upload lại
            if st.session_state.rag_mode.get("name") is None and saved_mode in {
                "RAG",
                "Graph RAG",
                "RAG, Graph RAG",
            }:
                st.session_state.rag_mode["name"] = saved_mode
            # Lưu config retriever để UI hiển thị; retriever object sẽ được set sau (nếu có FAISS local)
            st.session_state.retriever = {
                "mode": saved_mode,
                "retriever_k": saved_state.get("retriever_k"),
                "chunk_size": saved_state.get("chunk_size"),
                "chunk_overlap": saved_state.get("chunk_overlap"),
            }
        else:
            st.session_state.retriever = {
                "mode": None,
                "retriever_k": None,
                "chunk_size": None,
                "chunk_overlap": None
            }

    saved_doc = load_document_state(st.session_state.session_id)
    if saved_doc:
        st.session_state.document_meta = saved_doc
        st.session_state.documents = saved_doc.get("documents", [])
        st.session_state.uploaded_file_name = saved_doc.get("file_name")
        # Đồng bộ UI steps + graph triples từ DB (refresh chỉ load DB)
        st.session_state.rag_mode["step"] = saved_doc.get("steps", []) or []
        st.session_state.graph_triples = saved_doc.get("graph_triples", []) or []
        if saved_doc.get("mode") in {
            "RAG",
            "Graph RAG",
            "RAG, Graph RAG",
        }:
            st.session_state.rag_mode["name"] = saved_doc.get("mode")
        if saved_doc.get("retrieval_k"):
            st.session_state.retrieval_k = saved_doc.get("retrieval_k")

    vector_dir = os.path.join("vectorstores", st.session_state.session_id)
    if os.path.exists(vector_dir):
        st.session_state.vector_db = FAISS.load_local(
            vector_dir,
            Config.EMBEDDER,
            allow_dangerous_deserialization=True,
        )
        retriever_k = st.session_state.retrieval_k or 4
        st.session_state.retriever = st.session_state.vector_db.as_retriever(
            search_kwargs={"k": retriever_k}
        )

        # Nếu chưa có mode từ DB, fallback về RAG để UI chat vẫn hoạt động.
        if st.session_state.rag_mode.get("name") is None:
            st.session_state.rag_mode["name"] = "RAG"
    
    