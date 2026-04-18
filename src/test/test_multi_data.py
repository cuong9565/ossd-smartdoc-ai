import pytest
from langchain_core.documents import Document

import src.core.ingest as ingest
from src.core.filtering import filter_documents
import src.advanced.benchmark_retrievers as benchmark_retrievers
from src.core.ingest import ingest_uploaded_files
from langchain_core.embeddings import Embeddings
class FakeUpLoad:
  def __init__(self, name, file_type, data=b"fake-bytes"):
    self.name = name
    self.file_type = file_type
    self.type = file_type
    self.data = data
    
  def getbuffer(self):
    return self.data

class FakeEmbedder:
  def embed_documents(self, texts):
    return [[len(text) , sum(ord(c) for c in text) % 97] for text in texts]
  def embed_query(self, text):
    return [len(text) , sum(ord(c) for c in text) % 97]

class FakeLLM:
  def invoke(self, prompt):
    return "fake-answer"

def make_docs():
    return [
        Document(
            page_content="a",
            metadata={
                "page": 0,
                "source": "a.pdf",
                "file_type": "pdf",
                "upload_date": "2026-04-16",
                "chunk_index": 1,
            },
        ),
        Document(
            page_content="b",
            metadata={
                "page": 1,
                "source": "b.docx",
                "file_type": "docx",
                "upload_date": "2026-04-15",
                "chunk_index": 1,
            },
        ),
        Document(
            page_content="c",
            metadata={
                "page": 2,
                "source": "c.pdf",
                "file_type": "pdf",
                "upload_date": "2026-04-16",
                "chunk_index": 1,
            },
        ),
    ]

  
def test_ingest_uploaded_files_add_metadata(monkeypatch):
  def fake_load_file(temp_path, suffix):
    docs = [
      Document(page_content= "A", metadata={"page": 1, "chunk_index": 1}),
      Document(page_content= "B", metadata={"page": 1, "chunk_index": 2}),
    ]
    return 0.01, docs
  monkeypatch.setattr(ingest, "load_file", fake_load_file)
  uploaded_files = [
    FakeUpLoad("test.pdf", "application/pdf"),
    FakeUpLoad(
      "file_b.docx",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ),
  ]
  documents = ingest.ingest_uploaded_files(uploaded_files, 100, 20)
  assert documents
  assert {doc.metadata['source'] for doc in documents} == {"test.pdf", "file_b.docx"}
  assert {doc.metadata["file_type"] for doc in documents} == {"pdf", "docx"}
  
  for doc in documents:
        assert "doc_id" in doc.metadata
        assert "upload_date" in doc.metadata
        assert "chunk_index" in doc.metadata

class FakeEmbedder(Embeddings):
      
  def embed_documents(self, texts):
      return [[len(text), sum(ord(c) for c in text) % 97] for text in texts]
  def embed_query(self, text):
      return [len(text), sum(ord(c) for c in text) % 97]
    
def test_benchmark_retriever_returns_vector_and_hybrid_results(monkeypatch):
    documents = make_docs()
    
    monkeypatch.setattr(
      benchmark_retrievers.Config,
      "get_embedder",
      lambda: FakeEmbedder()
    )
    monkeypatch.setattr(
      benchmark_retrievers.Config,
      "get_llm",
      lambda: FakeLLM()
    )
  
    class FakeHybridRetriever:
      def __init__(self, documents, embedder, dense_k=30, sparse_k=30, top_k=5, alpha=0.7):
        self.docs = documents
        self.top_k = top_k 
      
      def invoke(self, query):
          return self.docs[: self.top_k]
    
    monkeypatch.setattr(benchmark_retrievers, "HybridRetriever", FakeHybridRetriever)
  
    results = benchmark_retrievers.benchmark_retriever(
        questions=["Nhập câu hỏi bất kỳ"],
        documents=documents,
        retrieval_k=3,
    )
    assert len(results) == 1
    row = results[0]
  
    assert row["question"] == "Nhập câu hỏi bất kỳ"
    assert "pure_retrieval_time" in row
    assert "hybrid_retrieval_time" in row
    assert "pure_generation_time" in row
    assert "hybrid_generation_time" in row
    assert "pure_answer" in row
    assert "hybrid_answer" in row
  
    assert isinstance(row["pure_answer"], str)
    assert isinstance(row["hybrid_answer"], str)
  
    assert row["pure_total_time"] >= 0
    assert row["hybrid_total_time"] >= 0
  
    assert row["pure_top_pages"]
    assert row["hybrid_top_pages"]