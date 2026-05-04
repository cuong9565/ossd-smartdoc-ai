import os
import tempfile
import streamlit as st
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PDFPlumberLoader, Docx2txtLoader    # đọc nội dung file PDF hoặc word
import time

from .metadata import assign_chunk_index_metadata, add_document_metadata

def ingest_uploaded_files(stepcurr, numstep, uploaded_files, chunk_size, chunk_overlap):
  """
  Ingest uploaded files and split them into chunks.
  
  Args:
      stepcurr (int): Current step number
      numstep (int): Total number of steps
      uploaded_files (list): List of uploaded files
      chunk_size (int): Size of each chunk
      chunk_overlap (int): Overlap between chunks
  
  Returns:
      list: List of documents
  """
  step = st.empty()
  step_string = f"📖 Bước {stepcurr}/{numstep}: Trích xuất văn bản và chunking tài liệu..."
  step.markdown(step_string)
  start_time = time.time()

  # danh sách chứa tất cả chunks của mọi file
  all_docs = []
  
  for uploaded_file in uploaded_files:
    # xác định của đuôi file
    suffix = ".pdf" if uploaded_file.type == 'application/pdf' else '.docx'
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
      tmp.write(uploaded_file.getbuffer())
      temp_path = tmp.name
    try:
        _, docs = load_file(temp_path, suffix)
        splitter = RecursiveCharacterTextSplitter(
          chunk_size=int(chunk_size),
          chunk_overlap=int(chunk_overlap)
        )
        chunks = splitter.split_documents(docs)
        chunks = assign_chunk_index_metadata(chunks)
        chunks = add_document_metadata(chunks, src_name=uploaded_file.name, file_type=suffix.replace(".", ""))
        # gom tất cả chunks vào list chung
        step_string = f"{step_string}  \nĐã tách từ file {uploaded_file.name} thành {len(chunks)} chunks"
        step.markdown(step_string)
        all_docs.extend(chunks)
    finally:
      if os.path.exists(temp_path):
        os.remove(temp_path)

  elapsed = round(time.time() - start_time, 2)
  step.success(f"📖 Trích xuất và chunking tài liệu trong {elapsed}s")
  st.session_state.rag_mode["step"].append(f"📖 Trích xuất và chunking tài liệu trong **{elapsed}s**")
  st.session_state.documents = all_docs
  return all_docs

def load_file(temp_path, suffix):
    start_time = time.time()
    if suffix == ".pdf":
        loader = PDFPlumberLoader(temp_path)
    else:
        loader = Docx2txtLoader(temp_path)
    docs = loader.load()
    elapsed = round(time.time() - start_time, 2) # Thời gian chạy load_file
    return elapsed, docs