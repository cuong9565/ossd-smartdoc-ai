import time

# lưu vector và tìm kiếm similarity
import streamlit as st
from langchain_community.tools.youtube import search
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter  # chia text thành các đoạn nhỏ
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain.retrievers import ContextualCompressionRetriever
from .config import Config
from ..advanced import assign_chunk_index_metadata


def chunk_file(chunk_size: int, chunk_overlap: int, docs):
    start_time = time.time()
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=int(chunk_size),
        chunk_overlap=int(chunk_overlap)
    )

    # 
    # split docs into chunk list
    # Each chunk have struct
        # page_content: content of chunk,
        # metadata: {
        #     ...,
        #     page: number of page,
        # }
    # Return documents (List chunks)
    # #
    documents = text_splitter.split_documents(docs)

    # Assign chunk_index for each chunk in documents
    documents = assign_chunk_index_metadata(documents)

    # Time to excecute chunk_pdf
    elapsed = round(time.time() - start_time, 2)

    # Save chunks to session
    st.session_state.document_chunks = len(documents)

    return elapsed, documents


def embedding(documents, retrieval_k):
    start_time = time.time()

    # 1. BẮT BUỘC: Kiểm tra tài liệu rỗng để tránh lỗi IndexError của FAISS
    if not documents or len(documents) == 0:
        st.error("Lỗi: Tài liệu rỗng hoặc không trích xuất được văn bản (có thể do file PDF là ảnh scan).")
        return 0

    embedder = Config.EMBEDDER
    vector_db = FAISS.from_documents(documents, embedder)

    total_chunks = len(documents)

    # 2. Khởi tạo retriever lấy số lượng document lớn hơn (lọc thô)
    safe_k = min(total_chunks, int(retrieval_k) * 3)
    base_retriever = vector_db.as_retriever(
        search_type="similarity",
        search_kwargs={"k": safe_k}
    )

    # 3. Tạo cross-encoder và compressor (chỉ giữ lại đúng retrieval_k)
    safe_top_n = min(total_chunks, int(retrieval_k))
    model = HuggingFaceCrossEncoder(model_name="cross-encoder/mmarco-mMiniLMv2-L12-H384-v1")
    compressor = CrossEncoderReranker(model=model, top_n=safe_top_n)

    # 4. Tạo compressor retriever
    compression_retriever = ContextualCompressionRetriever(
        base_compressor=compressor,
        base_retriever=base_retriever
    )

    elapsed = round(time.time() - start_time, 2)

    # Save vector database to session
    st.session_state.vector_db = vector_db

    # Save retriever to session
    st.session_state.retriever = vector_db.as_retriever(
        search_type="similarity",
        search_kwargs={"k": retrieval_k}
    )

    return elapsed, vector_db, compression_retriever