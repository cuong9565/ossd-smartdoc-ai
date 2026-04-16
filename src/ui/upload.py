import streamlit as st

# #
# Function: hiển thị ui cho phép upload file pdf hoặc word
# @return uploaded_file: file sau khi đã upload
# #
def render_upload_ui():
    with st.container():
        st.subheader("📤 Tải file pdf hoặc word")

        uploaded_file = st.file_uploader(
            "Chọn file PDF hoặc WORD",
            type=["pdf", "docx"]
        )
        
    return uploaded_file