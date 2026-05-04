import time
from langchain_community.vectorstores import FAISS
from ..core.config import Config
from .hybrid_search import HybridRetriever
from ..core.prompt_template import (
  detect_is_vietnamese,
  get_english_template,
  get_vietnamese_template,
)


def _build_prompt(question, context, history_text=""):
  if detect_is_vietnamese(question):
    return get_vietnamese_template(history_text, context, question)
  return get_english_template(history_text, context, question)


def _collect_context(docs):
  return "\n".join([doc.page_content for doc in docs])


def _run_pipeline(retriever, question, history_text=""):
  retrieval_start = time.perf_counter()
  docs = retriever.invoke(question)
  retrieval_time = time.perf_counter() - retrieval_start

  context = _collect_context(docs)
  prompt = _build_prompt(question, context, history_text)

  generation_start = time.perf_counter()
  answer = Config.get_llm().invoke(prompt)
  generation_time = time.perf_counter() - generation_start

  total_time = retrieval_time + generation_time

  return {
    "answer": answer,
    "retrieval_time": round(retrieval_time, 4),
    "generation_time": round(generation_time, 4),
    "total_time": round(total_time, 4),
    "top_pages": [doc.metadata.get("page", -1) for doc in docs],
    "context_length": len(context),
    "num_chunks": len(docs),
  }

def benchmark_retriever(questions, documents, retrieval_k):
  vector_db = FAISS.from_documents(documents, Config.get_embedder())
  pure_retriever = vector_db.as_retriever(search_type="similarity", search_kwargs={"k": int(retrieval_k)},)
  
  hybrid_retriever = HybridRetriever(
    documents = documents,
    embedder = Config.get_embedder(),
    dense_k = int(retrieval_k),
    sparse_k = int(retrieval_k),
    top_k = int(retrieval_k),
    alpha = 0.6,
    use_rerank=False,
  )

  # Warm-up to reduce first-run bias in timing
  if questions:
    warmup_question = questions[0]
    _run_pipeline(pure_retriever, warmup_question)
    _run_pipeline(hybrid_retriever, warmup_question)
  
  results = []
  for question in questions:
    pure_result = _run_pipeline(pure_retriever, question)
    hybrid_result = _run_pipeline(hybrid_retriever, question)

    results.append({
      "question": question,
      "pure_retrieval_time": pure_result["retrieval_time"],
      "pure_generation_time": pure_result["generation_time"],
      "pure_total_time": pure_result["total_time"],
      "pure_top_pages": pure_result["top_pages"],
      "pure_context_length": pure_result["context_length"],
      "pure_num_chunks": pure_result["num_chunks"],
      "pure_answer": pure_result["answer"],
      "hybrid_retrieval_time": hybrid_result["retrieval_time"],
      "hybrid_generation_time": hybrid_result["generation_time"],
      "hybrid_total_time": hybrid_result["total_time"],
      "hybrid_top_pages": hybrid_result["top_pages"],
      "hybrid_context_length": hybrid_result["context_length"],
      "hybrid_num_chunks": hybrid_result["num_chunks"],
      "hybrid_answer": hybrid_result["answer"],
    })
  return results

  
  