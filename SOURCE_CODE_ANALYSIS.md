# SmartDoc AI - Document Q&A System

## Tổng quan hệ thống

SmartDoc AI là hệ thống hỏi đáp tài liệu thông minh sử dụng công nghệ RAG (Retrieval Augmented Generation) được xây dựng trên Streamlit.

### Công nghệ sử dụng
- **LLM**: qwen2.5:7b (chạy local qua Ollama)
- **Embedding**: sentence-transformers/paraphrase-multilingual-mpnet-base-v2
- **Vector DB**: FAISS
- **Framework**: Streamlit

---

## Các bước xử lý trong hệ thống

### 1. Khởi tạo ứng dụng (app.py)

```
1. Import các module cần thiết
   ├── torch (disable torch.classes.__path__)
   ├── streamlit
   ├── src.core (init_sessions_state)
   ├── src.ui (các hàm render)
   ├── src.advanced (render_chunk_config)
   └── src.ui.multi_document_*
```

```python
# filepath: app.py
def main():
    # Bước 1: Khởi tạo session state
    init_sessions_state()
    
    # Bước 2: Load UI
    render_page()
    load_css()
    
    # Bước 3: Hiển thị sidebar và lấy rag_mode
    rag_mode = render_sidebar()
    
    # Bước 4: Hiển thị header
    render_header()
    
    # Bước 5: Hiển thị cấu hình chunking
    chunk_size, chunk_overlap, retrieval_k = render_chunk_config()
    
    # Bước 6: UI upload file
    uploaded_file = render_upload_ui()
    
    # Bước 7: UI hiển thị trạng thái tài liệu
    render_document_status_ui()
    
    # Bước 8: Xử lý tài liệu (RAG pipeline)
    document_processing(uploaded_file, chunk_size, chunk_overlap, retrieval_k, rag_mode)
    
    # Bước 9: UI chat history và chat question
    render_chat_section()
```

---

### 2. Khởi tạo Session State (src/core/sessions.py)

```
1. Khởi tạo chat_history_ui (danh sách cuộc hội thoại)
   └── Cấu trúc mỗi message:
       ├── role: "user" | "ai"
       ├── content: nội dung câu hỏi/phản hồi
       ├── timestamp: thời điểm
       ├── response_time: thời gian phản hồi
       ├── sources: danh sách nội dung liên quan
       ├── keywords: từ khóa liên quan
       └── mode: "RAG" | "Graph RAG"

2. Khởi tạo các biến trạng thái
   ├── rag_mode: "RAG" | "Graph RAG" | "RAG, Graph RAG"
   ├── graph_triples: danh sách triples từ knowledge graph
   ├── retriever: vector retriever
   ├── vector_db: FAISS database
   ├── uploaded_file_name: tên file đã upload
   ├── document_chunks: số lượng chunks
   ├── documents: danh sách documents
   └── retrieval_k: số lượng documents truy xuất
```

---

### 3. Cấu hình hệ thống (src/core/config.py)

```
1. Cấu hình Embedding
   └── EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
       ├── Sử dụng HuggingFaceEmbeddings
       ├── device: 'cpu'
       └── normalize_embeddings: True

2. Cấu hình LLM
   └── LLM = OllamaLLm(
       ├── model: "qwen2.5:7b"
       ├── temperature: 0.7
       ├── top_p: 0.9
       └── repeat_penalty: 1.1
   )

3. Cấu hình chat history
   └── NUMBER_CLOSEST_CHAT = 6 (3 cặp câu hỏi-phản hồi gần nhất)
```

---

### 4. Xử lý tài liệu - Pipeline chính (src/ui/document_processing.py)

#### Mode: RAG (Vector Search)

```
1. Kiểm tra điều kiện
   └── if uploaded_file AND retriever is None:
       ├── Kiểm tra kích thước file (max 50MB)
       └── Tạo file tạm với suffix .pdf hoặc .docx

2. Bước 1/3: Trích xuất văn bản (load_file)
   ├── Sử dụng PDFPlumberLoader cho PDF
   ├── Sử dụng Docx2txtLoader cho Word
   └── Trả về: elapsed time, danh sách docs (mỗi doc = 1 trang)

3. Bước 2/3: Chunking (chunk_file)
   ├── Sử dụng RecursiveCharacterTextSplitter
   │   ├── chunk_size: 100-2000 (default 500)
   │   └── chunk_overlap: 0-500 (default 50)
   ├── Gán chunk_index metadata cho mỗi chunk
   └── Trả về: elapsed time, danh sách documents (chunks)

4. Bước 3/3: Tạo Vector Embeddings (embedding)
   ├── Tạo FAISS vector database từ documents
   │   └── Sử dụng Config.EMBEDDER (MPNet)
   ├── Tạo retriever với k=retrieval_k
   │   └── search_type: "similarity"
   └── Lưu vào session_state:
       ├── vector_db
       └── retriever
```

```python
# Code minh họa chunking
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=int(chunk_size),
    chunk_overlap=int(chunk_overlap)
)
documents = text_splitter.split_documents(docs)
# Mỗi chunk có cấu trúc:
# {
#     page_content: "nội dung text",
#     metadata: {page: 1, chunk_index: 1, source: "file.pdf", ...}
# }
```

#### Mode: Graph RAG

```
1. Bước 1/4: Trích xuất văn bản (giống RAG)
   └── load_file(temp_path, suffix)

2. Bước 2/4: Chunking (giống RAG)
   └── chunk_file(chunk_size, chunk_overlap, docs)

3. Bước 3/4: Trích xuất Entity & Relation (extract_triples)
   ├── Sử dụng spaCy (en_core_web_sm)
   ├── Với mỗi sentence:
   │   ├── Tìm các VERB/AUX tokens là ROOT
   │   ├── Trích xuất subjects (nsubj, nsubjpass, csubj, agent, expl)
   │   ├── Trích xuất objects (dobj, obj, pobj, dative, attr, oprd, acomp)
   │   └── Tạo triple: (subject, relation, object)
   └── Trả về: elapsed time, danh sách triples

4. Bước 4/4: Xây dựng Knowledge Graph (build_graph)
   ├── Sử dụng NetworkX DiGraph
   ├── Với mỗi triple:
   │   ├── Nếu edge đã tồn tại: thêm relation vào danh sách
   │   └── Nếu edge chưa tồn tại: tạo edge mới
   └── Lưu graph ra file: graph.pkl (pickle)
```

```python
# Code minh họa extract_triples
for token in sent:
    if token.pos_ not in {"VERB", "AUX"} and token.dep_ != "ROOT":
        continue
    subjects = [child for child in token.lefts if child.dep_ in {"nsubj", "nsubjpass", ...}]
    objects = [child for child in token.rights if child.dep_ in {"dobj", "pobj", ...}]
    for subject in subjects:
        for obj in objects:
            triples.append((subject_text, relation, object_text))
```

#### Mode: RAG + Graph RAG (Kết hợp)

```
1. Chạy song song 2 pipeline:
   ├── Pipeline RAG: Bước 1/5 → 2/5 → 3/5
   └── Pipeline Graph: Bước 1/5 → 2/5 → 3/5 → 4/5 → 5/5

2. Lưu vào session_state:
   ├── vector_db (từ RAG)
   ├── retriever (từ RAG)
   ├── graph_triples (từ Graph)
   └── document_chunks
```

---

### 5. Xử lý câu hỏi - Q&A Pipeline (src/core/handle_answer_question.py)

```
1. Nhận câu hỏi từ user

2. Thêm câu hỏi vào chat_history_ui
   └── role: "user", content: question, timestamp

3. Xây dựng context theo mode:
   ├── RAG Mode:
   │   └── Dùng retriever.invoke(question) để tìm k chunks gần nhất
   │   └── context = "\n".join([doc.page_content for doc in relevant_docs])
   │
   └── Graph RAG Mode:
       └── Dùng graph_triples từ session_state
       └── context = "\n".join([f"{subject} | {relation} | {object}" ...])

4. Xây dựng history text
   └── Lấy NUMBER_CLOSEST_CHAT (6) message gần nhất
   └── Format: "User: ... | AI: ..."

5. Gọi LLM (_invoke_llm)
   ├── Detect ngôn ngữ câu hỏi (detect_is_vietnamese)
   ├── Chọn prompt template tương ứng
   │   ├── Tiếng Việt: get_vietnamese_template()
   │   └── English: get_english_template()
   └── Gọi Config.LLM.invoke(prompt)

6. Xây dựng message phản hồi
   └── role: "ai"
   └── content: response từ LLM
   └── sources: danh sách chunks đã truy xuất (với metadata page, chunk_index)
   └── keywords: từ khóa trích xuất từ câu hỏi
   └── response_time: thời gian xử lý

7. Thêm phản hồi vào chat_history_ui
```

```python
# Prompt template Vietnamese
prompt = f"""Bạn là một AI trợ lý thông minh, chuyên trả lời câu hỏi dựa trên tài liệu.
    Nhiệm vụ:
    - Chỉ sử dụng thông tin từ "Ngữ cảnh" để trả lời
    - Kết hợp với "Lịch sử hội thoại" để hiểu câu hỏi
    - Nếu không tìm thấy câu trả lời trong ngữ cảnh, hãy nói: "Tôi không biết"

    LỊCH SỬ HỘI THOẠI:
    {history_text}

    NGỮ CẢNH:
    {context}

    CÂU HỎI:
    {question}

    TRẢ LỜI (tiếng Việt):
"""
```

#### Multi-Mode (RAG + Graph RAG so sánh)

```
1. Thêm câu hỏi vào chat_history_ui

2. Gọi _build_message với mode="RAG"
   └── rag_message = {...}

3. Gọi _build_message với mode="Graph RAG"
   └── graph_message = {...}

4. Tạo dual message
   └── dual: True
   └── rag: rag_message
   └── graph: graph_message

5. Hiển thị 2 cột so sánh kết quả
```

---

### 6. Hybrid Search (src/advanced/hybrid_search.py)

```
1. Khởi tạo HybridRetriever
   ├── Tạo FAISS vector database (dense)
   ├── Tạo BM25Retriever (sparse)
   ├── Khởi tạo CrossEncoder reranker (bge-reranker-v2-m3)
   └── Tham số:
       ├── dense_k: 30 (số docs từ vector search)
       ├── sparse_k: 30 (số docs từ BM25)
       ├── top_k: 5 (số docs cuối cùng)
       ├── alpha: 0.7 (trọng số dense)
       └── rerank_k: 30

2. Invoke (tìm kiếm)
   ├── Gọi dense_retriever.invoke(query)
   │   └── Lấy top dense_k docs
   ├── Gọi sparse_retriever.invoke(query)
   │   └── Lấy top sparse_k docs
   ├── Tính điểm kết hợp:
   │   ├── dense: score += alpha / (rank + 1)
   │   └── sparse: score += (1-alpha) / (rank + 1)
   ├── Sắp xếp theo score giảm dần
   └── Rerank với CrossEncoder

3. Rerank
   ├── Deduplicate docs (theo page + chunk_index)
   ├── Tạo cặp (query, doc_content)
   ├── CrossEncoder.predict(pairs)
   ├── Sắp xếp theo score và lấy top_k
```

```python
# Code minh họa hybrid scoring
scores = defaultdict(float)
for rank, doc in enumerate(dense_docs):
    key = self._doc_key(doc)
    scores[key] += self.alpha / (rank + 1)  # Dense weight
    merged_docs[key] = doc

for rank, doc in enumerate(sparse_docs):
    key = self._doc_key(doc)
    scores[key] += (1 - self.alpha) / (rank + 1)  # Sparse weight
    merged_docs[key] = doc
```

---

### 7. Metadata xử lý (src/core/metadata.py)

```
1. assign_chunk_index_metadata
   ├── Đếm số chunks trong mỗi trang
   ├── Gán chunk_index cho từng chunk
   └── Cấu trúc: {chunk_index: 1, 2, 3...} theo từng page

2. add_document_metadata
   ├── Tạo doc_id (UUID)
   ├── Lấy upload_date (YYYY-MM-DD)
   ├── Gán metadata cho mỗi chunk:
   │   ├── source: tên file
   │   ├── doc_id: UUID
   │   ├── upload_date: ngày upload
   │   └── file_type: "pdf" hoặc "docx"
```

---

### 8. UI Components

#### 8.1 Sidebar (src/ui/sidebar.py)

```
1. Hiển thị header "SmartDoc AI"
2. Quick Guide (4 bước)
3. System Info (format, max size, language)
4. Models Info (LLM, Embedding, Vector DB)
5. Manage buttons
   ├── Clear Chat: xóa chat history
   └── Clear All: reset toàn bộ state
6. Mode selector
   ├── "RAG": vector search
   ├── "Graph RAG": knowledge graph
   └── "RAG, Graph RAG": so sánh cả 2
```

#### 8.2 Upload UI (src/ui/upload.py)

```
1. Hiển thị file_uploader
   ├── accept_multiple_files: False (mode đơn)
   ├── type: ["pdf", "docx"]
   └── max file size: 50MB (kiểm tra trong document_processing)
```

#### 8.3 Chat Section (src/ui/chat_section.py)

```
1. Render chat history
   ├── Hiển thị các message đã chat
   ├── Với dual mode: hiển thị 2 cột RAG vs Graph RAG
   └── Hiển thị sources (nguồn trích dẫn) expandable

2. Render chat input
   ├── Text area cho câu hỏi
   └── Nút submit

3. Render answer question
   ├── Progress bar (25% → 50% → 75% → 100%)
   ├── Gọi handle_answer_question() hoặc handle_answer_question_multi()
   └── st.rerun() để cập nhật UI
```

#### 8.4 Chunk Config (src/advanced/impove_chunk_strategy.py)

```
1. Chunk Size slider
   ├── min: 100, max: 2000, default: 500, step: 50

2. Chunk Overlap slider
   ├── min: 0, max: 500, default: 50, step: 10

3. Retrieval K slider
   ├── min: 1, max: 10, default: 5, step: 1
```

---

### 9. Multi-Document Processing (src/ui/multi_document_processing.py)

```
1. Upload nhiều files
   ├── st.file_uploader với accept_multiple_files=True
   └── Lưu vào session_state.uploaded_files

2. Cấu hình parameters
   ├── Chunk Size: 100-4000 (default 800)
   ├── Chunk Overlap: 0-400 (default 100)
   └── Retrieval K: 10-100 (default 30)

3. Xử lý (ingest_uploaded_files)
   ├── Với mỗi file:
   │   ├── Tạo temp file
   │   ├── load_file()
   │   ├── chunk_file()
   │   ├── assign_chunk_index_metadata()
   │   └── add_document_metadata()
   └── Gộp tất cả chunks vào all_docs

4. Lưu vào session_state
   ├── documents: all_docs
   └── retrieval_k
```

---

### 10. Multi-Document Chat (src/ui/multi_document_chat.py)

```
1. Kiểm tra documents đã upload

2. Nhập câu hỏi

3. Chọn mode search
   ├── Vector: FAISS only
   └── Hybrid: HybridRetriever

4. Tùy chọn benchmark
   └── run_benchmark: so sánh Vector vs Hybrid

5. Lọc metadata
   ├── Filter theo source (file name)
   ├── Filter theo file_type (pdf/docx)
   └── Filter theo upload_date

6. Xử lý câu hỏi
   ├── filter_documents() theo filters
   ├── answer_question() với mode
   └── Trả về answer + docs

7. Hiển thị kết quả
   ├── Answer text
   ├── Sources (file, page, chunk_index)
   └── Benchmark comparison (nếu chọn)
```

---

### 11. Benchmark Section (src/ui/benchmark_section.py)

```
1. Nhập câu hỏi benchmark

2. Chạy benchmark_retriever
   ├── Vector pipeline: FAISS retriever
   ├── Hybrid pipeline: HybridRetriever
   └── So sánh:
       ├── retrieval_time
       ├── generation_time
       ├── total_time
       ├── top_pages
       ├── context_length
       └── num_chunks

3. Hiển thị kết quả
   ├── 2 cột câu trả lời
   ├── Bảng metrics
   ├── Biểu đồ so sánh
   └── Metrics tóm tắt
```

---

### 12. Filtering (src/core/filtering.py)

```
1. filter_documents(documents, src, file_type, upload_date)
   ├── Lọc theo source (tên file)
   ├── Lọc theo file_type (pdf/docx)
   └── Lọc theo upload_date
   └── Trả về: filtered documents list
```

---

### 13. Language Detection (src/core/prompt_template.py)

```
1. detect_is_vietnamese(text)
   ├── Kiểm tra các ký tự tiếng Việt:
   │   ├── a: áàảãạăắằẳẵặâấầẩẫậ
   │   ├── e: éèẻẽẹêếềểễệ
   │   ├── i: íìỉĩị
   │   ├── o: óòỏõọôốồổỗộơớờởỡợ
   │   ├── u: úùủũụưứừửữự
   │   ├── y: ýỳỷỹỵ
   │   └── đ
   └── Return: True/False
```

---

## Sơ đồ luồng dữ liệu

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │  Upload  │→ │  Chunk   │→ │  Embed   │→ │    Chat      │   │
│  │  File    │  │  Config  │  │  (FAISS) │  │    Q&A       │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      PROCESSING PIPELINE                        │
│                                                                 │
│  1. LOAD FILE                                                  │
│     PDF → PDFPlumberLoader → Documents (pages)                 │
│     DOCX → Docx2txtLoader → Documents                           │
│                                                                 │
│  2. CHUNK                                                      │
│     Documents → RecursiveCharacterTextSplitter → Chunks       │
│     + assign_chunk_index_metadata                              │
│     + add_document_metadata                                    │
│                                                                 │
│  3. EMBEDDING                                                  │
│     Chunks → HuggingFaceEmbeddings → FAISS → Retriever        │
│                                                                 │
│  4. EXTRACT TRIPLES (Graph RAG)                                │
│     Chunks → spaCy → Triples → NetworkX Graph                 │
│                                                                 │
│  5. ANSWER                                                     │
│     Question → Retriever → Context → LLM (Qwen2.5) → Answer   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tổng kết các bước xử lý

| STT | Bước | Module | Chức năng |
|-----|------|--------|-----------|
| 1 | Init Session | sessions.py | Khởi tạo biến trạng thái |
| 2 | Load Config | config.py | Cấu hình LLM, Embedding |
| 3 | Upload File | upload.py | Nhận file PDF/DOCX |
| 4 | Load File | load_pdf_or_word.py | Trích xuất text từ file |
| 5 | Chunk | pdf_or_word_pipeline.py | Chia text thành chunks |
| 6 | Metadata | metadata.py | Gán metadata cho chunks |
| 7 | Embedding | pdf_or_word_pipeline.py | Tạo vector embeddings |
| 8 | Extract Triples | graph_rag.py | Trích xuất entity/relation |
| 9 | Build Graph | graph_rag.py | Xây dựng knowledge graph |
| 10 | Hybrid Search | hybrid_search.py | Kết hợp vector + BM25 |
| 11 | Filter | filtering.py | Lọc documents theo metadata |
| 12 | Detect Language | prompt_template.py | Phát hiện tiếng Việt/Anh |
| 13 | Build Prompt | prompt_template.py | Tạo prompt cho LLM |
| 14 | Invoke LLM | handle_answer_question.py | Gọi Qwen2.5 trả lời |
| 15 | Render Chat | chat_section.py | Hiển thị chat UI |
| 16 | Render Sources | chat_section.py | Hiển thị nguồn trích dẫn |

---

*Document created on April 24, 2026*
*SmartDoc AI - OSSD • Saigon University*