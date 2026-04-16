import time
from .config import Config
from langchain_community.document_loaders import PDFPlumberLoader    # đọc nội dung file PDF
from langchain_text_splitters import RecursiveCharacterTextSplitter  # chia text thành các đoạn nhỏ
from ..advanced import assign_chunk_index_metadata
from langchain_community.vectorstores import FAISS                   # lưu vector và tìm kiếm similarity

def load_pdf(temp_path):
    start_time = time.time()
    loader = PDFPlumberLoader(temp_path)
    docs = loader.load()
    elapsed = round(time.time() - start_time, 2) # Thời gian chạy load_pdf
    return elapsed, docs

def chunk_pdf(chunk_size: int, chunk_overlap: int, docs):
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
        #     total_pages: total page,
        # }
    # Return documents (List chunks)
    # #
    documents = text_splitter.split_documents(docs)

    # Assign chunk_index for each chunk in documents
    documents = assign_chunk_index_metadata(documents)

    # Time to excecute chunk_pdf
    elapsed = round(time.time() - start_time, 2)

    return elapsed, documents

def embedding(documents):
    start_time = time.time()
    embedder = Config.EMBEDDER
    vector_db = FAISS.from_documents(documents, embedder)
    elapsed = round(time.time() - start_time, 2)
    return elapsed, vector_db