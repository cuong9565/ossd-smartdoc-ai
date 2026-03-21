# OSSD SmartDoc AI

Ứng dụng AI cho phép upload file PDF và đặt câu hỏi trực tiếp trên nội dung tài liệu bằng mô hình RAG (Retrieval-Augmented Generation), chạy hoàn toàn local với Ollama.

---

## Demo

Chạy tại:
http://localhost:8501

---

## Tính năng

- Upload file PDF
- Tự động chia nhỏ tài liệu (chunking)
- Tìm kiếm ngữ nghĩa với FAISS
- Hỏi đáp thông minh dựa trên nội dung tài liệu
- Chạy hoàn toàn local (không cần API key)

---

## Yêu cầu hệ thống

sudo su
apt update
apt upgrade

# Python
python3 --version
apt install python3

# pip
pip3 --version
apt install python3-pip

# Ollama
ollama --version
snap install ollama

---

## Công nghệ sử dụng

- Python
- pip
- Ollama
- Streamlit
- LangChain
- FAISS

---

## Cài đặt lần đầu

# Clone project
git clone https://github.com/cuong9565/ossd-smartdoc-ai.git
cd ossd-smartdoc-ai

# Tạo virtual environment
python3.12 -m venv venv

# Kích hoạt môi trường
source venv/bin/activate

# Tải model (~4.7GB)
ollama pull qwen2.5:7b

# Kiểm tra model
ollama list

# Cài thư viện
pip install -r requirements.txt

---

## Chạy ứng dụng

source venv/bin/activate
streamlit run app.py

---

## Thư viện sử dụng (requirements.txt)

- streamlit
- langchain
- langchain-community
- langchain-text-splitters
- sentence-transformers
- transformers
- torch
- faiss-cpu
- pdfplumber
- pypdf
- numpy
- pandas

---

## Lưu ý

- Model qwen2.5:7b cần:
  + RAM tối thiểu: 8GB
  + Khuyến nghị: 16GB

- Nếu lỗi thiếu RAM:
  ollama pull qwen2.5:3b

---

## Troubleshooting

Lỗi: model requires more system memory
=> RAM không đủ → dùng model nhỏ hơn hoặc tăng RAM/swap

Lỗi Ollama không chạy:
ollama serve

Lỗi thiếu package:
pip install -r requirements.txt

---

## TODO

- Tối ưu tốc độ embedding
- Thêm nhiều model
- UI đẹp hơn
- Hỗ trợ nhiều file

---