import os
import tempfile
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..advanced.load_pdf_or_word import load_file
from .metadata import assign_chunk_index_metadata, add_document_metadata

def ingest_uploaded_files(uploaded_files, chunk_size, chunk_overlap):
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
        all_docs.extend(chunks)
    finally:
      if os.path.exists(temp_path):
        os.remove(temp_path)
  return all_docs
