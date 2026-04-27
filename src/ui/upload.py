import streamlit as st

# #
# Function: hiển thị ui cho phép upload file pdf hoặc word
# @return uploaded_file: file sau khi đã upload
# #
def render_upload_ui():
    uploaded_files = None
    
    if st.session_state.rag_mode["name"] is None:
        with st.container():
            st.subheader("📤 Tải file pdf hoặc word")

            uploaded_files = st.file_uploader(
                "Chọn file PDF hoặc WORD",
                type=["pdf", "docx"],
                accept_multiple_files=True,
            )
        
    return uploaded_files