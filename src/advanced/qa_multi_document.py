from ..advanced.hybrid_search import HybridRetriever
from ..core.filtering import filter_documents
from ..core.prompt_template import detect_is_vietnamese, get_english_template, get_vietnamese_template
from ..core.config import Config
from langchain_community.vectorstores import FAISS

def build_context(docs):
  parts = []
  for doc in docs:
    src = doc.metadata.get("source", "unknown")
    page = doc.metadata.get("page" , 0) + 1
    chunk_index = doc.metadata.get("chunk_index" , 0)
    parts.append(f"File: {src} | Page: {page} | Chunk: {chunk_index}\n{doc.page_content}")
  return "\n\n".join(parts)

def answer_question(question, documents, k, filters=None, mode="hybrid"):
  filtered_docs = filter_documents(
    documents,
    src = filters.get("source") if filters else None,
    file_type = filters.get("file_type") if filters else None,
    upload_date = filters.get("upload_date") if filters else None,
  )
  if not filtered_docs:
    return {"answer": "Không có document nào khớp với filter.", "docs":[]}

  # Chọn retriever theo mode
  if mode == "vector":
    vector_db = FAISS.from_documents(filtered_docs, Config.get_embedder())
    retriever = vector_db.as_retriever(
      search_type="similarity",
      search_kwargs={"k": int(k)},
    )
  else:
    retriever = HybridRetriever(
      filtered_docs,
      embedder=Config.get_embedder(),
      dense_k=k,
      sparse_k=k,
      top_k=k,
      alpha=0.6,
    )

  docs = retriever.invoke(question)
  context = build_context(docs)
  
  if detect_is_vietnamese(question):
    prompt_template = get_vietnamese_template("",context, question)
  else:
    prompt_template = get_english_template("",context, question)
  answer = Config.get_llm().invoke(prompt_template)
  return {
    "answer": answer,
    "docs": docs,
  }