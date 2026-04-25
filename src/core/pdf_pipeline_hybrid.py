import time

import streamlit as st
from langchain_community.document_loaders import PDFPlumberLoader  # Đọc nội dung file PDF.
from langchain_text_splitters import RecursiveCharacterTextSplitter  # Chia text thành các đoạn nhỏ.

from .config import Config
from ..advanced import HybridRetriever, assign_chunk_index_metadata


def load_pdf(temp_path):
    # Đo thời gian load PDF.
    start_time = time.time()

    # Đọc file PDF từ đường dẫn tạm.
    loader = PDFPlumberLoader(temp_path)
    docs = loader.load()

    # Trả về thời gian xử lý và danh sách trang.
    elapsed = round(time.time() - start_time, 2)
    return elapsed, docs


def chunk_pdf(chunk_size: int, chunk_overlap: int, docs):
    # Đo thời gian chunking.
    start_time = time.time()

    # Cắt văn bản thành các đoạn nhỏ để truy xuất tốt hơn.
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=int(chunk_size),
        chunk_overlap=int(chunk_overlap),
    )

    # Tách từng trang thành danh sách chunk.
    documents = text_splitter.split_documents(docs)

    # Gán chunk_index để hiển thị nguồn dễ hơn.
    documents = assign_chunk_index_metadata(documents)

    # Tính thời gian chunking.
    elapsed = round(time.time() - start_time, 2)

    # Lưu số lượng chunk vào session để UI hiển thị.
    st.session_state.document_chunks = len(documents)
    
    st.session_state.documents = documents 

    return elapsed, documents


def embedding(documents, retrieval_k):
    # Đo thời gian tạo hybrid retriever.
    start_time = time.time()

    # Lấy embedder từ cấu hình chung.
    embedder = Config.EMBEDDER
 
    # Tạo retriever hybrid: dense + sparse.
    hybrid_retriever = HybridRetriever(
        documents=documents,
        embedder=embedder,
        dense_k=int(retrieval_k),
        sparse_k=int(retrieval_k),
        top_k=int(retrieval_k),
        alpha=0.6,
    )

    # Lưu vector_db để debug hoặc tái sử dụng nếu cần.
    st.session_state.vector_db = hybrid_retriever.vector_db

    # Lưu retriever mới vào session để phần chat dùng lại.
    st.session_state.retriever = hybrid_retriever

    # Trả về thời gian tạo retriever.
    elapsed = round(time.time() - start_time, 2)
    return elapsed
