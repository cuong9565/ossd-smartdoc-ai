import streamlit as st
import tempfile
import os
import time
from src.core.metadata import extract_document_profile
from ..core import embedding
from ..advanced import extract_triples, build_graph, save_graph
from src.presistance.history_manager import save_document_state_full, save_retriever_state
from src.core.ingest import ingest_uploaded_files
from src.advanced.hybrid_search import HybridRetriever
from src.core.config import Config


def _normalize_uploaded_files(uploaded_files):
    if not uploaded_files:
        return []
    # streamlit.file_uploader(accept_multiple_files=True) trả về List[UploadedFile]
    # nhưng đôi khi code cũ truyền vào 1 UploadedFile đơn lẻ
    return uploaded_files if isinstance(uploaded_files, list) else [uploaded_files]


def document_processing(uploaded_file, chunk_size, chunk_overlap, retrieval_k, rag_mode):
    uploaded_files = _normalize_uploaded_files(uploaded_file)
    if uploaded_files and st.session_state.rag_mode["name"] is None:
        total_size_mb = sum([(f.size or 0) for f in uploaded_files]) / (1024 * 1024)
        
        # If size file > 100MB
        if total_size_mb > 100:
            st.error(f"❌ Tổng dung lượng file quá lớn ({total_size_mb:.2f}MB > 100MB)")
            return

        st.session_state.rag_mode["name"] = rag_mode
        st.session_state.rag_mode["step"] = []
        st.session_state.uploaded_file_name = [f.name for f in uploaded_files]
        st.session_state.graph_triples = []
        st.session_state.documents = []
        st.session_state.document_meta = None
        st.session_state.is_processing = True
        
        try:
            with st.status("🔄 Đang xử lý tài liệu...", expanded=True):
                # Multi-file: ingest trực tiếp thành chunks + metadata
                # (đảm bảo mỗi chunk có source/file_type/upload_date/doc_id/chunk_index)

                if rag_mode == "RAG":
                    documents = ingest_uploaded_files(1, 2, uploaded_files, chunk_size, chunk_overlap)
                    _ = _do_step_embedding(2, 2, documents, retrieval_k)
                    st.session_state.documents = documents
                elif rag_mode == "Graph RAG":
                    documents = ingest_uploaded_files(1, 4, uploaded_files, chunk_size, chunk_overlap)
                    _ = _do_step_embedding(2, 4, documents, retrieval_k)
                    triples = _do_step_extract_triples(3, 4, documents)
                    _ = _do_step_build_graph(4, 4, triples)
                    st.session_state.documents = documents
                else:
                    documents = ingest_uploaded_files(1, 4, uploaded_files, chunk_size, chunk_overlap)
                    _ = _do_step_embedding(2, 4, documents, retrieval_k)
                    triples = _do_step_extract_triples(3, 4, documents)
                    _ = _do_step_build_graph(4, 4, triples)
                    st.session_state.documents = documents

                # Build Hybrid retriever once (for chat "Hybrid" mode)
                # Use wider candidate pools than top_k for better recall.
                k = int(retrieval_k) if retrieval_k else 4
                try:
                    st.session_state.hybrid_retriever = HybridRetriever(
                        documents=documents,
                        embedder=Config.get_embedder(),
                        dense_k=max(30, k * 3),
                        sparse_k=max(30, k * 3),
                        rerank_k=max(30, k * 6),
                        top_k=k,
                        alpha=0.6,
                        use_rerank=False,
                    )
                except Exception:
                    # Không để lỗi build hybrid làm hỏng flow ingest
                    st.session_state.hybrid_retriever = None

                save_retriever_state(st.session_state.session_id, rag_mode, retrieval_k, chunk_size, chunk_overlap)
                save_document_state_full(
                    st.session_state.session_id,
                    st.session_state.uploaded_file_name,
                    rag_mode,
                    chunk_size,
                    chunk_overlap,
                    retrieval_k,
                    documents,
                    st.session_state.rag_mode.get("step", []),
                    st.session_state.get("graph_triples", []),
                )
                st.session_state.document_meta = {
                    "session_id": st.session_state.session_id,
                    "file_name": st.session_state.uploaded_file_name,
                    "mode": rag_mode,
                    "chunk_size": chunk_size,
                    "chunk_overlap": chunk_overlap,
                    "retrieval_k": retrieval_k,
                    "documents": documents,
                }
                vector_dir = os.path.join("vectorstores", st.session_state.session_id)
                os.makedirs(vector_dir, exist_ok=True)
                st.session_state.vector_db.save_local(vector_dir)

        finally:
            st.session_state.is_processing = False
        st.rerun()

def _do_step_embedding(stepcurr, numstep, documents, retrieval_k):
    step = st.empty()
    step.write(f"🔢 Bước {stepcurr}/{numstep}: Tạo vector embeddings...")
    elapsed, vector_db, retriever = embedding(documents, retrieval_k)
    step.success(f"🔢 Embedding {vector_db.index.ntotal} vector, {vector_db.index.d} chiều trong **{elapsed}s**")
    st.session_state.rag_mode["step"].append(f"🔢 Embedding {vector_db.index.ntotal} vector, {vector_db.index.d} chiều trong **{elapsed}s**")
    st.session_state.vector_db = vector_db
    st.session_state.retriever = retriever
    return None

def _do_step_extract_triples(stepcurr, numstep, documents):
    step = st.empty()
    step.write(f"🧠 Bước {stepcurr}/{numstep}: Trích xuất thực thể & quan hệ...")
    elapsed, triples = extract_triples(documents)
    step.success(f"🧠 Trích xuất {len(triples)} triples trong **{elapsed}s**")
    st.session_state.rag_mode["step"].append(f"🧠 Trích xuất {len(triples)} triples trong **{elapsed}s**")
    return triples

def _do_step_build_graph(stepcurr, numstep, triples):
    step = st.empty()
    step.write(f"🕸️ Bước {stepcurr}/{numstep}: Xây dựng graph...")
    elapsed, graph = build_graph(triples)
    save_graph(graph)
    step.success(f"🕸️ Xây dựng  trong **{elapsed}s**")
    st.session_state.graph_triples = triples
    st.session_state.rag_mode["step"].append(f"🕸️ Xây dựng  trong **{elapsed}s**")
    return None


def _do_step_extract_profile(stepcurr, numstep, documents):
    start_time = time.time()

    # Lấy profile và lưu vào session_state
    profile = extract_document_profile(documents)
    st.session_state.document_profile = profile

    elapsed = round(time.time() - start_time, 2)

    # Hiển thị log trên UI giống các bước khác
    st.write(f"📄 Bước {stepcurr}/{numstep}: Nhận diện tài liệu... ({elapsed}s)")
    st.info(f"Lĩnh vực nhận diện: {profile}")  # In ra để người dùng thấy

    return profile