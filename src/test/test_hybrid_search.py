import importlib
from types import SimpleNamespace

from langchain_core import documents

import pytest
from langchain_core.documents import Document

hybrid_search = importlib.import_module("src.advanced.hybrid_search")
HybridRetriever = hybrid_search.HybridRetriever

def make_doc(page_content, page, chunk_index):
    return Document(
        page_content=page_content,
        metadata={
            "page": page,
            "chunk_index": chunk_index,
        },
    )

class FakeRetriever:
    def __init__(self, docs):
      self.docs = docs
    def invoke(self, query):
      return self.docs
    
class FakeVectorDB:
    def __init__(self, docs):
      self.docs = docs
    def as_retriever(self, search_type = None, search_kwargs = None):
      return FakeRetriever(self.docs)

class FakeRanker:
    def __init__(self, scores):
      self.scores = scores
      self.received_pairs = None

    def predict(self, pairs):
      self.received_pairs = pairs
      return self.scores[: len(pairs)]      
    
def test_content_key_normalization():
   retriever = object.__new__(HybridRetriever)
   key1 = retriever._content_key("  Hello   World  ")
   key2 = retriever._content_key("Hello World")
   key3 = retriever._content_key("        hello                 world")
   assert key1 == key2 == key3

def test_trim_limits_length():
    retriever = object.__new__(HybridRetriever)
    retriever.max_rerank = 10
    text = "asdfasdfasdf"
    trimmed = retriever._trim_text(text)
    assert len(trimmed) == 10
    assert trimmed == "asdfasdfas"

def test_dedupe_docs_removes_duplicate_doc_and_content():
    retriever = object.__new__(HybridRetriever)
    retriever._doc_key = HybridRetriever._doc_key.__get__(retriever)
    retriever._content_key = HybridRetriever._content_key.__get__(retriever)
    docs = [
      make_doc("Hello World", page=1, chunk_index=1),
      make_doc("Hello World", page=1, chunk_index=1),
      make_doc("Hello World", page=1, chunk_index=2),
      make_doc("Khác nhau", page=3, chunk_index=1),
    ]
    unique_docs = retriever._dedupe_docs(docs)
    assert len(unique_docs) == 2
    assert unique_docs[1].metadata["page"] == 3
    assert unique_docs[1].metadata["chunk_index"] == 1
    
def test_rerank_sorts_by_score(monkeypatch):
    fake_vector_db = FakeVectorDB([])
    fake_ranker = FakeRanker(scores=[0.9, 0.5, 0.2])
    def fake_from_documents(docs, embedder):
      return fake_vector_db
    class FakeBM25:
        @classmethod
        def from_documents(cls, docs):
          return SimpleNamespace(k = 0)
             
    class FakeCrossEncoder:
        def __init__(self, model_name, device):
          pass 
    monkeypatch.setattr(hybrid_search.FAISS, "from_documents", fake_from_documents)
    monkeypatch.setattr(hybrid_search.BM25Retriever, "from_documents", FakeBM25.from_documents)
    monkeypatch.setattr(hybrid_search, "CrossEncoder", FakeCrossEncoder) 

    retriever = HybridRetriever(
        documents = [],
        embedder=None,
        top_k = 3,
        rerank_k = 3,
        max_rerank = 8,
        use_rerank=True,
    )
    retriever.reranker = fake_ranker
    docs = [
        make_doc("abcdefghijk", page=1, chunk_index=1),
        make_doc("doc two", page=1, chunk_index=2),
        make_doc("doc three", page=1, chunk_index=3),
    ]
    result = retriever.rerank("query text", docs)
    assert len(result) == 3
    assert result[0].metadata["chunk_index"] == 1
    assert result[1].metadata["chunk_index"] == 2
    assert result[2].metadata["chunk_index"] == 3

    assert fake_ranker.received_pairs[0][1] == "abcdefgh"
    assert fake_ranker.received_pairs[1][1] == "doc two"

def test_rerank_with_empty_docs():
    retriever = object.__new__(HybridRetriever)
    empty_docs =[]
    result = retriever.rerank("query text", empty_docs)

    assert result == []
    assert len(result) == 0