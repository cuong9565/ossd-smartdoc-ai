from langchain_community.document_loaders import PDFPlumberLoader, Docx2txtLoader    # đọc nội dung file PDF hoặc word
import time

def load_file(temp_path, suffix):
    start_time = time.time()
    if suffix == ".pdf":
        loader = PDFPlumberLoader(temp_path)
    else:
        loader = Docx2txtLoader(temp_path)
    docs = loader.load()
    elapsed = round(time.time() - start_time, 2) # Thời gian chạy load_file
    return elapsed, docs
