import streamlit as st
from ..core.ingest import ingest_uploaded_files

def render_multi_document_processing():
  st.subheader("Upload nhiều tài liệu")
  
  uploaded_files = st.file_uploader("Chọn file PDF hoặc WORD", type=["pdf", "docx"], accept_multiple_files=True)
  
  if uploaded_files:
    st.session_state.uploaded_files = uploaded_files
    st.success("Tài liệu đã được upload thành công")
  else:
    st.error("Vui lòng upload tài liệu")

  col1, col2, col3 = st.columns(3)
  with col1:
    chunk_size = st.number_input("Chunk Size", min_value=100, max_value=4000, value=800, step=50)
  with col2:
    chunk_overlap = st.number_input("Chunk Overlap", min_value=0, max_value=400, value=100, step=10)
  with col3:
    retrieval_k = st.number_input("Retrieval K", min_value=10, max_value=100, value=30, step=5)

  if st.button("Xử lý tài liệu"):
    if not uploaded_files:
      st.error("Vui lòng upload ít nhất 1 file")
      return
    with st.spinner("Đang xử lý tài liệu..."):
      try:
        documents = ingest_uploaded_files(uploaded_files, chunk_size, chunk_overlap)

        st.session_state.documents = documents
        st.session_state.retrieval_k = retrieval_k
        st.success("Tài liệu đã được xử lý thành công")
        
        st.markdown("### Danh sách file đã upload")
        for file in uploaded_files:
          st.write(f"- {file.name}")
        
      except Exception as e:
        st.error(f"Lỗi khi xử lý tài liệu: {e}")
      
    
