import streamlit as st

def render_document_status_ui():
    if st.session_state.rag_mode["name"] is not None:
        with st.expander(label="📂 Danh sách tài liệu", expanded=False):
            st.success(st.session_state.uploaded_file_name)

        with st.expander(label="📄 Thông tin xử lý tài liệu", expanded=False):
            st.success(f"Chế độ: **{st.session_state.rag_mode["name"]}**")
            for step in st.session_state.rag_mode["step"]:
                st.success(step)