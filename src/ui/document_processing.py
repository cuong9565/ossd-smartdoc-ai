import streamlit as st
import tempfile
import os
from ..core import chunk_file, embedding
from ..advanced import load_file, extract_triples, build_graph, save_graph

def document_processing(uploaded_file, chunk_size, chunk_overlap, retrieval_k, rag_mode):
    if uploaded_file and st.session_state.rag_mode is None:
        file_size_mb = uploaded_file.size / (1024 * 1024)

        if file_size_mb > 50:
            st.error(f"❌ File quá lớn ({file_size_mb:.2f}MB > 50MB)")
            return

        suffix = ".pdf" if uploaded_file.type == "application/pdf" else ".docx"

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.getbuffer())
            temp_path = tmp.name

        st.session_state.rag_mode = rag_mode
        st.session_state.uploaded_file_name = uploaded_file.name
        st.session_state.graph_triples = []

        try:
            if rag_mode == "RAG, Graph RAG":
                with st.status("🔄 Đang xử lý tài liệu...", expanded=True) as status:
                    step1 = st.empty()
                    step1.write("📖 Bước 1/5: Trích xuất văn bản...")
                    elapsed1, docs = load_file(temp_path, suffix)
                    step1.success(f"✓ {len(docs)} trang trong {elapsed1}s")

                    step2 = st.empty()
                    step2.write("✂️ Bước 2/5: Chunking...")
                    elapsed2, documents = chunk_file(chunk_size, chunk_overlap, docs)
                    step2.success(f"✓ {len(documents)} chunks trong {elapsed2}s")
                    st.session_state.document_chunks = len(documents)

                    step3 = st.empty()
                    step3.write("🔢 Bước 3/5: Tạo vector embeddings...")
                    elapsed3, vector_db, retriever = embedding(documents, retrieval_k)
                    step3.success(f"✓ Embedding xong trong {elapsed3}s")
                    st.session_state.vector_db = vector_db
                    st.session_state.retriever = retriever

                    step4 = st.empty()
                    step4.write("🧠 Bước 4/5: Trích xuất thực thể & quan hệ...")
                    elapsed4, triples = extract_triples(documents)
                    step4.success(f"✓ {len(triples)} triples trong {elapsed4}s")
                    st.session_state.graph_triples = triples

                    step5 = st.empty()
                    step5.write("🕸️ Bước 5/5: Xây dựng graph...")
                    elapsed5, graph = build_graph(triples)
                    elapsed6, save_path = save_graph(graph)
                    step5.success("✓ Xây dựng graph thành công!")

                    left_col, right_col = st.columns(2)

                    with left_col:
                        st.write("✅ RAG hoàn tất")
                        st.write(f"📄 Pages: {len(docs)}")
                        st.write(f"✂️ Chunks: {len(documents)}")
                        st.write(f"🔗 Embedding: {elapsed3}s")
                        st.write(f"⏱️ Time: {round(elapsed1 + elapsed2 + elapsed3, 2)}s")

                    with right_col:
                        st.write("✅ Graph hoàn tất")
                        st.write(f"📄 Pages: {len(docs)}")
                        st.write(f"✂️ Chunks: {len(documents)}")
                        st.write(f"🔗 Triples: {len(triples)}")
                        st.write(f"🔗 Build Graph: {elapsed5}s")
                        st.write(f"🔗 Save Graph: {save_path}")
                        st.write(f"⏱️ Time: {round(elapsed4 + elapsed5 + elapsed6, 2)}s")

                    status.update(
                        label="Tài liệu đã xử lý thành công!",
                        state="complete",
                        expanded=False
                    )

            elif rag_mode == "Graph RAG":
                process_graph(
                    st.container(),
                    temp_path,
                    suffix,
                    chunk_size,
                    chunk_overlap,
                    retrieval_k,
                )
            else:
                process_rag(st.container(), temp_path, suffix, chunk_size, chunk_overlap, retrieval_k)
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
        st.rerun()

def process_rag(container, temp_path, suffix, chunk_size, chunk_overlap, retrieval_k):
    with container:
        with st.status("🔄 Đang phân tích tài liệu...", expanded=True) as status:
            try:
                step1 = st.empty()
                step1.write("📖 Bước 1/3: Trích xuất văn bản...")
                elapsed, docs = load_file(temp_path, suffix)
                step1.success(f"✓ Trích xuất xong: {len(docs)} trang trong {elapsed}s")

                step2 = st.empty()
                step2.write("✂️ Bước 2/3: Chia nhỏ văn bản thành chunks...")
                elapsed, documents = chunk_file(chunk_size, chunk_overlap, docs)
                step2.success(f"✓ Chunking xong: {len(documents)} chunks trong {elapsed}s")
                st.session_state.document_chunks = len(documents)

                step3 = st.empty()
                step3.write("🔢 Bước 3/3: Tạo vector embeddings...")
                elapsed, vector_db, retriever = embedding(documents, retrieval_k)
                step3.success(f"✓ Embedding xong trong {elapsed}s")
                st.session_state.vector_db = vector_db
                st.session_state.retriever = retriever

                status.update(
                    label="File đã xử lý thành công!",
                    state="complete",
                    expanded=False
                )
                st.success(
                    ":material/check_circle: **Tài liệu sẵn sàng!**  \n"
                    "Bạn có thể bắt đầu đặt câu hỏi được rồi."
                )

            except Exception as e:
                status.update(
                    label="❌ Xử lý thất bại",
                    state="error",
                    expanded=True
                )
                st.error(
                    f"""
                    **Có lỗi xảy ra khi xử lý tài liệu**
                    **Chi tiết lỗi:**
                    {str(e)}
                    """,
                    icon="🚨"
                )

def process_graph(container, temp_path, suffix, chunk_size, chunk_overlap, retrieval_k=None):
    with container:
        with st.status("🔄 Đang xây dựng Knowledge Graph...", expanded=True) as status:
            try:
                step1 = st.empty()
                step1.write("📖 Bước 1/4: Trích xuất văn bản...")
                elapsed, docs = load_file(temp_path, suffix)
                step1.success(f"✓ {len(docs)} trang trong {elapsed}s")

                step2 = st.empty()
                step2.write("✂️ Bước 2/4: Chunking...")
                elapsed, documents = chunk_file(chunk_size, chunk_overlap, docs)
                step2.success(f"✓ {len(documents)} chunks trong {elapsed}s")
                st.session_state.document_chunks = len(documents)

                step3 = st.empty()
                step3.write("🧠 Bước 3/4: Trích xuất thực thể & quan hệ...")
                elapsed, triples = extract_triples(documents)
                step3.success(f"✓ {len(triples)} triples trong {elapsed}s")

                step4 = st.empty()
                step4.write("🕸️ Bước 4/4: Xây dựng graph...")
                graph = build_graph(triples)
                save_graph(graph)
                step4.success("✓ Xây dựng graph thành công!")
                st.session_state.graph_triples = triples

                if retrieval_k is not None:
                    _, vector_db, retriever = embedding(documents, retrieval_k)
                    st.session_state.vector_db = vector_db
                    st.session_state.retriever = retriever

                status.update(
                    label="Graph RAG hoàn tất!",
                    state="complete",
                    expanded=False
                )

                st.success(
                    "🧠 **Knowledge Graph đã sẵn sàng!**  \n"
                    "Bạn có thể truy vấn theo ngữ nghĩa nâng cao."
                )

            except Exception as e:
                status.update(
                    label="❌ Graph RAG thất bại",
                    state="error",
                    expanded=True
                )
                st.error(f"Lỗi: {str(e)}", icon="🚨")

def rag_pipeline(temp_path, suffix, chunk_size, chunk_overlap, retrieval_k):
    elapsed1, docs = load_file(temp_path, suffix)
    elapsed2, documents = chunk_file(chunk_size, chunk_overlap, docs)
    elapsed3, vector_db, retriever = embedding(documents, retrieval_k)

    return {
        "docs": f"{len(docs)} ({elapsed1}s)",
        "chunks": f"{len(documents)} ({elapsed2}s)",
        "embedding": f"{elapsed3}s",
        "time": elapsed1 + elapsed2 + elapsed3,
        "documents": documents,
        "vector_db": vector_db,
        "retriever": retriever
    }

def graph_pipeline(temp_path, suffix, chunk_size, chunk_overlap, retrieval_k=None):
    elapsed1, docs = load_file(temp_path, suffix)
    elapsed2, documents = chunk_file(chunk_size, chunk_overlap, docs)
    elapsed3, triples = extract_triples(documents)
    elapsed4, graph = build_graph(triples)
    elapsed5, savegraph = save_graph(graph)

    result = {
        "docs": f"{len(docs)} ({elapsed1}s)",
        "chunks": f"{len(documents)} ({elapsed2}s)",
        "triples": f"{len(triples)} ({elapsed3}s)",
        "build_graph": f"{elapsed4}s",
        "save_graph": f"{elapsed5}",
        "documents": documents,
        "triples_data": triples,
    }

    if retrieval_k is not None:
        elapsed6, vector_db, retriever = embedding(documents, retrieval_k)
        result.update({
            "vector_db": vector_db,
            "retriever": retriever,
            "embedding": f"{elapsed6}s",
            "time": elapsed1 + elapsed2 + elapsed3 + elapsed4 + elapsed5 + elapsed6,
        })
    else:
        result["time"] = elapsed1 + elapsed2 + elapsed3 + elapsed4 + elapsed5

    return result