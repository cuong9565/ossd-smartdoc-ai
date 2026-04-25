import streamlit as st

def render_chunk_config():
    chunk_size = 0
    chunk_overlap = 0
    retrieval_k = 0

    if st.session_state.rag_mode is None:
        with st.expander("⚙️ **Cấu hình Chunking**", expanded=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                chunk_size = st.slider(
                    "Chunk Size",
                    min_value=100,
                    max_value=2000,
                    value=500,
                    step=50,
                    help="Kích thước mỗi đoạn văn bản",
                    label_visibility="collapsed"
                )
                st.caption(f"📐 Size: {chunk_size} ký tự")
            
            with col2:
                chunk_overlap = st.slider(
                    "Chunk Overlap",
                    min_value=0,
                    max_value=500,
                    value=50,
                    step=10,
                    help="Overlap giữa chunks",
                    label_visibility="collapsed"
                )
                st.caption(f"🔗 Overlap: {chunk_overlap} ký tự")
            
            with col3:
                retrieval_k = st.slider(
                    "Top-K Nguồn",
                    min_value=1,
                    max_value=10,
                    value=5,
                    step=1,
                    help="Số chunks truy xuất từ FAISS (dùng cho cả LLM và hiển thị nguồn)",
                    label_visibility="collapsed"
                )
                st.caption(f"📚 Top-K: {retrieval_k} nguồn")

    return chunk_size, chunk_overlap, retrieval_k