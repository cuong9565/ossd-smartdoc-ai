import streamlit as st

def render_upload_ui():
    with st.container():
        st.subheader("📤 Upload File PDF")

        uploaded_file = st.file_uploader(
            "Chọn file PDF",
            type=["pdf"]
        )
        
    return uploaded_file