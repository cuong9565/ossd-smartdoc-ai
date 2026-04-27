import streamlit as st

def render_document_status_ui():
    if st.session_state.get("is_processing", False):
        return

    if st.session_state.rag_mode["name"] is not None:
        document_meta = st.session_state.get("document_meta") or {}
        documents = st.session_state.get("documents") or []
        mode_name = document_meta.get("mode") or st.session_state.rag_mode["name"]

        with st.expander(label="📂 Danh sách tài liệu", expanded=False):
            file_name = document_meta.get("file_name") or st.session_state.uploaded_file_name or "None"
            # uploaded_file_name có thể là list khi multi-file
            if isinstance(file_name, list):
                st.success(", ".join(file_name))
            else:
                st.success(file_name)
            st.caption(f"📄 Số chunks: {len(documents)}")

        with st.expander(label="📄 Thông tin xử lý tài liệu", expanded=False):
            st.success(f"Chế độ: **{mode_name}**")
            if document_meta.get("chunk_size") is not None:
                st.success(f"✂️ Chunk size: {document_meta.get('chunk_size')}")
            if document_meta.get("chunk_overlap") is not None:
                st.success(f"🔗 Chunk overlap: {document_meta.get('chunk_overlap')}")
            if document_meta.get("retrieval_k") is not None:
                st.success(f"🔎 Retrieval K: {document_meta.get('retrieval_k')}")
            if "Graph RAG" in str(mode_name):
                graph_triples = st.session_state.get("graph_triples") or []
                st.success(f"🧠 Graph triples: {len(graph_triples)}")

            shown_steps = []
            for step in st.session_state.rag_mode["step"]:
                if step and step not in shown_steps:
                    shown_steps.append(step)

            for step in shown_steps:
                st.success(step)