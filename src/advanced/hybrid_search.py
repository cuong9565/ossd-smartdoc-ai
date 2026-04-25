import hashlib
from collections import defaultdict

import torch
from langchain_community.retrievers import BM25Retriever
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from sentence_transformers import CrossEncoder


class HybridRetriever: 
  def __init__(self, documents, embedder, dense_k = 30, sparse_k = 30, top_k = 5, alpha = 0.7, rerank_k = 30, max_rerank = 1200):
    self.embedder = embedder
    self.vector_db = FAISS.from_documents(documents, embedder)
    self.dense_retriever = self.vector_db.as_retriever(search_type="similarity", search_kwargs={"k": dense_k})
    self.sparse_retriever = BM25Retriever.from_documents(documents)
    self.sparse_retriever.k = sparse_k
    self.top_k = int(top_k)
    self.alpha = alpha
    self.rerank_k = int(rerank_k)
    self.max_rerank = int(max_rerank)
    self.device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[SmartDoc] HybridRetriever device: {self.device}")
    self.reranker = CrossEncoder("BAAI/bge-reranker-v2-m3", device=self.device)

  def _doc_key(self, doc):
    page = doc.metadata.get("page", -1)
    chunk_index = doc.metadata.get("chunk_index", -1) 
    return (page, chunk_index)
  
  def _content_key(self, text:str)->str:
    normalized = " ".join(text.lower().split())
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()
  
  def _trim_text(self, text: str) -> str:
    text = " ".join(text.split())
    if(len(text) <= self.max_rerank):
      return text
    return text[: self.max_rerank]

  def _dedupe_docs(self, docs):
    seen_doc_keys = set()
    unique_docs = []
    seen_content_keys = set()
    for doc in docs:
      doc_key = self._doc_key(doc)
      content_key = self._content_key(doc.page_content)
      if doc_key in seen_doc_keys:
        continue
      if content_key in seen_content_keys:
        continue
      seen_doc_keys.add(doc_key)
      unique_docs.append(doc)
      seen_content_keys.add(content_key)
    return unique_docs

  
  def rerank(self, query, docs):
    if not docs:
      return []
    docs = self._dedupe_docs(docs)
    pairs = [(query, self._trim_text(doc.page_content)) for doc in docs]
    print(f"[SmartDoc] Rerank candidates: {len(pairs)}")
    scores = self.reranker.predict(pairs)
    reranked = sorted(zip(scores, docs), key=lambda x: x[0], reverse=True)
    return [doc for _, doc in reranked][:self.top_k]
  
  def invoke(self, query: str) -> list[Document]:
    dense_docs = self.dense_retriever.invoke(query)
    sparse_docs = self.sparse_retriever.invoke(query)
    
    scores = defaultdict(float)
    
    merged_docs = {} 
    for rank, doc in enumerate(dense_docs):
      key = self._doc_key(doc)
      scores[key] += self.alpha / (rank + 1)
      merged_docs[key] = doc
    
    for rank, doc in enumerate(sparse_docs):
      key = self._doc_key(doc)
      scores[key] += (1 - self.alpha) / (rank + 1)
      merged_docs[key] = doc

    ordered_docs = [
      merged_docs[key] for key in sorted(merged_docs.keys(), key=lambda k: scores[k], reverse=True)
    ]
    print(f"[SmartDoc] Fusion docs: {len(ordered_docs)} | Rerank limit: {self.rerank_k}")
    return self.rerank(query, ordered_docs[: self.rerank_k]) 