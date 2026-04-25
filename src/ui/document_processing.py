import streamlit as st
import tempfile
import os
import time
from src.core.metadata import extract_document_profile
from ..core import chunk_file, embedding
from ..advanced import load_file, extract_triples, build_graph, save_graph

def document_processing(uploaded_file, chunk_size, chunk_overlap, retrieval_k, rag_mode):
    if uploaded_file and st.session_state.rag_mode["name"] is None:
        file_size_mb = uploaded_file.size / (1024 * 1024)
        
        # If size file > 100MB10
        if file_size_mb > 100:
            st.error(f"❌ File quá lớn ({file_size_mb:.2f}MB > 100MB)")
            return
        
        # Check if suffix uploaded_file is pdf or word
        suffix = ".pdf" if uploaded_file.type == "application/pdf" else ".docx"

        # Save temporary file to memory
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.getbuffer())
            temp_path = tmp.name

        st.session_state.rag_mode["name"] = rag_mode
        st.session_state.rag_mode["step"] = []
        st.session_state.uploaded_file_name = uploaded_file.name
        st.session_state.graph_triples = []
        try:
            with st.status("🔄 Đang xử lý tài liệu...", expanded=True):
                if rag_mode == "RAG":

                    docs = _do_step_load_file(stepcurr=1, numstep=4, temp_path=temp_path, suffix=suffix)
                    documents = _do_step_chunk_file(stepcurr=2, numstep=4, chunk_size=chunk_size,
                                                    chunk_overlap=chunk_overlap, docs=docs)
                    profile = _do_step_extract_profile(stepcurr=3, numstep=4, documents=documents)

                    _ = _do_step_embedding(stepcurr=4, numstep=4, documents=documents, retrieval_k=retrieval_k)

                elif rag_mode == "Graph RAG":
                    docs = _do_step_load_file(stepcurr=1, numstep=6, temp_path=temp_path, suffix=suffix)
                    documents = _do_step_chunk_file(stepcurr=2, numstep=6, chunk_size=chunk_size,
                                                    chunk_overlap=chunk_overlap, docs=docs)
                    profile = _do_step_extract_profile(stepcurr=3, numstep=6, documents=documents)
                    _ = _do_step_embedding(stepcurr=4, numstep=6, documents=documents, retrieval_k=retrieval_k)
                    triples = _do_step_extract_triples(stepcurr=5, numstep=6, documents=documents)
                    _ = _do_step_build_graph(stepcurr=6, numstep=6, triples=triples)

                else:

                    docs = _do_step_load_file(stepcurr=1, numstep=6, temp_path=temp_path, suffix=suffix)
                    documents = _do_step_chunk_file(stepcurr=2, numstep=6, chunk_size=chunk_size,
                                                    chunk_overlap=chunk_overlap, docs=docs)
                    profile = _do_step_extract_profile(stepcurr=3, numstep=6, documents=documents)
                    _ = _do_step_embedding(stepcurr=4, numstep=6, documents=documents, retrieval_k=retrieval_k)
                    triples = _do_step_extract_triples(stepcurr=5, numstep=6, documents=documents)
                    _ = _do_step_build_graph(stepcurr=6, numstep=6, triples=triples)

        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
        st.rerun()

def _do_step_load_file(stepcurr, numstep, temp_path, suffix):
    step = st.empty()
    step.write(f"📖 Bước {stepcurr}/{numstep}: Trích xuất văn bản...")
    elapsed, docs = load_file(temp_path, suffix)
    step.success(f"📖 Trích xuất {len(docs)} trang trong {elapsed}s")
    st.session_state.rag_mode["step"].append(f"📖 Trích xuất {len(docs)} trang trong **{elapsed}s**")
    return docs

def _do_step_chunk_file(stepcurr, numstep, chunk_size, chunk_overlap, docs):
    step = st.empty()
    step.write(f"✂️ Bước {stepcurr}/{numstep}: Chia nhỏ văn bản thành chunks...")
    elapsed, documents = chunk_file(chunk_size, chunk_overlap, docs)
    step.success(f"✂️ Chunking {len(documents)} chunks trong {elapsed}s")
    st.session_state.rag_mode["step"].append(f"✂️ Chunking {len(documents)} chunks trong **{elapsed}s**")
    return documents

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