from datetime import datetime
from uuid import uuid4

def assign_chunk_index_metadata(documents):
  page_counters = {}
  for chunk in documents:
    page_number = chunk.metadata.get('page', 0)
    page_counters[page_number] = page_counters.get(page_number, 0) + 1
    chunk.metadata['chunk_index'] = page_counters[page_number] 
  return documents

def add_document_metadata(documents, src_name, file_type):
  doc_id = str(uuid4())
  upload_date = datetime.now().strftime("%Y-%m-%d")
  
  for chunk in documents:
    chunk.metadata['source'] = src_name
    chunk.metadata['doc_id'] = doc_id
    chunk.metadata['upload_date'] = upload_date
    chunk.metadata['file_type'] = file_type
  return documents
