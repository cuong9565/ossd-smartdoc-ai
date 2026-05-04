from datetime import datetime
from uuid import uuid4

from src.core.prompt_template import get_file_context_template


def assign_chunk_index_metadata(documents):
  page_counters = {}
  for chunk in documents:
    page_number = chunk.metadata.get('page', 0)
    page_counters[page_number] = page_counters.get(page_number, 0) + 1
    chunk.metadata['chunk_index'] = page_counters[page_number] 
  return documents


from langchain.prompts import PromptTemplate
from src.core.config import Config


def extract_document_profile(documents) -> str:
  # Lấy nội dung của tối đa 15 chunk/trang đầu tiên
  sample_text = "\n".join([doc.page_content for doc in documents[:15]])

  template = get_file_context_template()

  prompt = PromptTemplate(template=template, input_variables=["text"])
  chain = prompt | Config.LLM

  profile = chain.invoke({"text": sample_text}).strip()
  return profile

def add_document_metadata(documents, src_name, file_type):
  doc_id = str(uuid4())
  upload_date = datetime.now().strftime("%Y-%m-%d")
  
  for chunk in documents:
    chunk.metadata['source'] = src_name
    chunk.metadata['doc_id'] = doc_id
    chunk.metadata['upload_date'] = upload_date
    chunk.metadata['file_type'] = file_type
  return documents
