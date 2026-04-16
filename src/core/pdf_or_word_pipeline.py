import time
from .config import Config
from langchain_text_splitters import RecursiveCharacterTextSplitter  # chia text thành các đoạn nhỏ
from ..advanced import assign_chunk_index_metadata
from langchain_community.vectorstores import FAISS                   # lưu vector và tìm kiếm similarity
import streamlit as st

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
    embedder = Config.EMBEDDER
    vector_db = FAISS.from_documents(documents, embedder)
    elapsed = round(time.time() - start_time, 2)

    # Save vector database to session
    st.session_state.vector_db = vector_db

    # Save retriever to session
    st.session_state.retriever = vector_db.as_retriever(   
        search_type="similarity",
        search_kwargs={"k": int(retrieval_k)}
    )

    return elapsed