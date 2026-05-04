# SmartDoc AI - Source Code Structure Analysis

## 📋 Overview

SmartDoc AI là một hệ thống Q&A thông minh dựa trên tài liệu, sử dụng RAG (Retrieval-Augmented Generation) và Graph RAG để trả lời câu hỏi từ tài liệu PDF/Word.

## 🏗️ Main Application Structure (`app.py`)

### `main()` function - Entry Point
**Chức năng:** Hàm chính khởi động ứng dụng Streamlit

**Flow chính:**
1. **Init DB + Session State**
   - `init_db()` - Khởi tạo database SQLite
   - `init_sessions_state()` - Khởi tạo session state của Streamlit

2. **Load UI Components**
   - `render_page()` - Cấu hình trang Streamlit
   - `load_css()` - Tải styles CSS
   - `render_sidebar()` - Render sidebar với controls
   - `render_header()` - Render header của trang

3. **Configuration**
   - `render_chunk_config()` - UI cấu hình chunking parameters

4. **File Upload**
   - `render_upload_ui()` - UI upload files
   - Lưu uploaded files vào session state

5. **Document Processing**
   - `render_document_status_ui()` - Hiển thị status tài liệu
   - `document_processing()` - Xử lý tài liệu đã upload

6. **Chunk Evaluation Mode**
   - Nếu `enable_chunk_evaluation` = True:
     - `render_chunk_direct_evaluation_section()` - Đánh giá chunks trực tiếp
     - `return` - Kết thúc flow, không hiển thị chat

7. **Chat Interface**
   - `render_chat_section()` - UI chat và Q&A

---

## 🗄️ Database Layer (`src/presistance/db.py`)

### `init_db()` function
**Chức năng:** Khởi tạo database SQLite với các bảng cần thiết

**Các bảng được tạo:**
1. **`retriever_state`** - Lưu trạng thái retriever
   - `session_id` - ID phiên làm việc
   - `mode` - Chế độ RAG (RAG/Graph RAG)
   - `retriever_k` - Số lượng documents truy xuất
   - `chunk_size` - Kích thước chunk
   - `chunk_overlap` - Overlap giữa chunks

2. **`chat_messages`** - Lưu lịch sử chat
   - `session_id` - ID phiên
   - `role` - user/ai
   - `content` - Nội dung tin nhắn
   - `response_time` - Thời gian phản hồi
   - `mode` - Chế độ sử dụng
   - `sources` - Nguồn trích dẫn
   - `keywords` - Từ khóa

3. **`document_state`** - Lưu trạng thái tài liệu
   - `session_id` - ID phiên
   - `file_name` - Tên file
   - `mode` - Chế độ xử lý
   - `documents` - Documents đã xử lý
   - `steps_json` - Các bước xử lý
   - `graph_triples_json` - Triples từ Graph RAG

### `getConnection()` function
**Chức năng:** Tạo kết nối đến database SQLite
- Thiết lập `row_factory = sqlite3.Row` để dễ dàng truy cập dữ liệu
- Trả về connection object

---

## 🧠 Session Management (`src/core/sessions.py`)

### `init_sessions_state()` function
**Chức năng:** Khởi tạo tất cả session state variables

**Các session variables được khởi tạo:**

1. **RAG Mode State**
   - `rag_mode` - Object chứa mode và steps
     - `name`: "RAG" | "Graph RAG" | "RAG, Graph RAG"
     - `step`: List các bước xử lý

2. **Graph RAG State**
   - `graph_triples` - List triples từ knowledge graph
   - `last_dual_responses` - Response từ dual mode

3. **Vector Database State**
   - `vector_db` - FAISS database object
   - `retriever` - Retriever object
   - `hybrid_retriever` - Hybrid retriever cache

4. **Processing State**
   - `use_rerank` - Toggle cross-encoder reranking
   - `is_processing` - Flag đang xử lý
   - `enable_chunk_evaluation` - Flag đánh giá chunking

5. **Document State**
   - `uploaded_file_name` - Tên file đã upload
   - `documents` - List documents
   - `document_meta` - Metadata tài liệu
   - `retrieval_k` - Số lượng retrieval

6. **Chat State**
   - `chat_history_ui` - Lịch sử hội thoại UI
   - `search_mode` - "Vector" | "Hybrid"

7. **Session Management**
   - `session_id` - UUID cho mỗi phiên
   - Load từ URL parameters hoặc tạo mới
   - Restore state từ database nếu có

**Logic phục hồi state:**
1. Load retriever state từ DB
2. Load document state từ DB  
3. Load chat history từ DB
4. Load vector store từ disk nếu tồn tại
5. Restore FAISS retriever nếu có vector store

---

## 🎨 UI Components (`src/ui/`)

### `render_page()` (`src/ui/page.py`)
**Chức năng:** Cấu hình trang Streamlit
- `st.set_page_config()` với:
  - `page_title`: "SmartDoc AI"
  - `page_icon`: ":material/description:"
  - `layout`: "wide"
  - `initial_sidebar_state`: "expanded"

### `load_css()` (`src/ui/styles.py`)
**Chức năng:** Tải CSS styles cho toàn bộ ứng dụng

**Các nhóm styles:**
1. **Global Styles** - Font, background, colors
2. **Sidebar Styling** - Background #2C2F33 gradient
3. **Button Styling** - Hover effects, transitions
4. **File Uploader** - Border styling, hover effects
5. **Form Elements** - Text areas, inputs
6. **Cards & Containers** - Answer cards, source cards
7. **Headers & Text** - Typography hierarchy
8. **Chat Messages** - Message styling
9. **Citation & Source Tracking** - Highlight, badges
10. **Animations** - FadeIn, Pulse effects
11. **Utility Classes** - Colors, text styles

### `render_sidebar()` (`src/ui/sidebar.py`)
**Chức năng:** Render sidebar với controls và thông tin

**Các sections:**

1. **Header** - Logo và branding
2. **Quick Guide** - 4 steps hướng dẫn nhanh
3. **System Info** - Format, max size, language
4. **Model Config** - LLM, Embedding, Vector DB info
5. **Manage Actions** (khi có mode)
   - **Clear Chat** - Xóa lịch sử chat
   - **Clear All** - Reset toàn bộ ứng dụng
     - Xóa DB state
     - Xóa vector store files
     - Reset session state
6. **Mode Selection** (khi chưa có mode)
   - Selectbox: "RAG" | "Graph RAG" | "RAG, Graph RAG"
7. **Chunking Evaluation**
   - Checkbox: "Bật chế độ đánh giá chunking"
   - Lưu vào `enable_chunk_evaluation`
8. **Footer** - Copyright info

**Logic Clear All:**
- Clear chat history from DB
- Clear retriever state from DB
- Clear document state from DB
- Remove vector store directory
- Reset all session state variables
- Show toast notification

### `render_header()` (`src/ui/header.py`)
**Chức năng:** Render header của trang
- HTML styling với center alignment
- Title: "🚀 SmartDoc AI"
- Subtitle: "Intelligent Document Q&A System"

### `render_upload_ui()` (`src/ui/upload.py`)
**Chức năng:** Render file upload interface

**Logic:**
- Chỉ hiển thị khi `rag_mode["name"]` is None
- `st.file_uploader()` với:
  - Type: ["pdf", "docx"]
  - `accept_multiple_files=True`
- Return uploaded files list

### `render_document_status_ui()` (`src/ui/document_status.py`)
**Chức năng:** Hiển thị status và thông tin tài liệu

**Các expandable sections:**

1. **📂 Danh sách tài liệu**
   - Hiển thị tên files đã upload
   - Số lượng chunks: `len(documents)`

2. **📄 Thông tin xử lý tài liệu**
   - Chế độ: RAG/Graph RAG
   - Chunk size, overlap, retrieval_k
   - Graph triples (nếu Graph RAG)
   - Processing steps từ `rag_mode["step"]`

### `render_chat_section()` (`src/ui/chat_section.py`)
**Chức năng:** Render chat interface và xử lý Q&A

**Các components:**

1. **Chat History** - `render_chat_history()`
   - Hiển thị các tin nhắn user/ai
   - Support dual responses (RAG + Graph RAG)
   - Benchmark responses comparison
   - Source citations với highlighting

2. **Chat Input** - `render_chat_input()`
   - Search mode: Vector/Hybrid radio
   - Re-ranking checkbox
   - Benchmark checkbox
   - Question textarea với form submit

3. **Answer Processing** - `render_answer_question()`
   - Handle single/multi mode responses
   - Benchmark mode comparison
   - Error handling

**Key Functions:**
- `highlight_text()` - Highlight keywords trong text
- `render_sources_ui()` - Render source cards với badges

### `document_processing()` (`src/ui/document_processing.py`)
**Chức năng:** Xử lý tài liệu đã upload

**Main Flow:**
1. **Validate files** - Check size limit (100MB)
2. **Set processing state** - `is_processing = True`
3. **Process by mode:**
   - **RAG**: Ingest → Embed
   - **Graph RAG**: Ingest → Embed → Extract Triples → Build Graph
   - **RAG, Graph RAG**: Combined flow
4. **Build Hybrid Retriever** - For search mode options
5. **Save state** - Database + vector store
6. **Cleanup** - Set `is_processing = False`

**Helper Functions:**
- `_normalize_uploaded_files()` - Chuẩn hóa uploaded files
- `_do_step_embedding()` - Tạo vector embeddings
- `_do_step_extract_triples()` - Extract knowledge graph triples
- `_do_step_build_graph()` - Build and save graph
- `_do_step_extract_profile()` - Extract document profile

---

## ⚙️ Advanced Features (`src/advanced/`)

### `render_chunk_config()` (`src/advanced/impove_chunk_strategy.py`)
**Chức năng:** UI cấu hình chunking parameters

**3 sliders trong expander:**
1. **Chunk Size** - 100-2000, default 500, step 50
2. **Chunk Overlap** - 0-500, default 50, step 10  
3. **Top-K Nguồn** - 1-10, default 5, step 1

**Return:** `(chunk_size, chunk_overlap, retrieval_k)`

### `render_chunk_direct_evaluation_section()` (`src/advanced/chunk_direct_evaluation.py`)
**Chức năng:** Đánh giá chất lượng chunks trực tiếp bằng intrinsic metrics

**Main Function: `evaluate_chunks_directly()`**
- Input: uploaded_files, chunk_configs
- Output: Dict với kết quả đánh giá chi tiết

**Các nhóm metrics:**
1. **Basic Metrics** - Độ dài, variance, range
2. **Sentence Metrics** - Số câu, completeness, boundary violations
3. **Coherence Metrics** - Local coherence, internal coherence, stability
4. **Boundary Quality** - Alignment với natural breaks
5. **Content Coverage** - Bao phủ ký tự/từ, duplication
6. **Structural Metrics** - Paragraphs, length balance, consistency

**UI Features:**
- Bảng so sánh 12 cấu hình
- Biểu đồ trực quan hóa
- Bảng xếp hạng chất lượng
- Phân tích theo chunk size

**Configuration:**
- Chunk sizes: 500, 1000, 1500, 2000
- Overlaps: 50, 100, 200
- Tổng: 12 cấu hình tự động

---

## 🔧 Core Processing (`src/core/`)

### `ingest_uploaded_files()` (`src/core/ingest.py`)
**Chức năng:** Load và chunk documents từ uploaded files

**Process:**
1. Load files với PDFPlumberLoader/Docx2txtLoader
2. Chunk với RecursiveCharacterTextSplitter
3. Assign metadata (chunk index, document info)
4. Return processed chunks

---

## 📊 Data Flow Summary

```
app.py (main)
├── init_db() → Create SQLite tables
├── init_sessions_state() → Setup session variables
├── render_page() → Configure Streamlit page
├── load_css() → Apply styles
├── render_sidebar() → Show controls & get rag_mode
├── render_header() → Show header
├── render_chunk_config() → Get chunking params
├── render_upload_ui() → Get uploaded files
├── render_document_status_ui() → Show document info
├── document_processing() → Process documents
│   ├── ingest_uploaded_files() → Load & chunk
│   ├── _do_step_embedding() → Create vectors
│   ├── _do_step_extract_triples() → Extract KG
│   └── _do_step_build_graph() → Build graph
├── render_chunk_direct_evaluation_section() → Evaluate chunks
└── render_chat_section() → Q&A interface
    ├── render_chat_history() → Show history
    ├── render_chat_input() → Get question
    └── render_answer_question() → Process answer
```

## 🎯 Key Design Patterns

1. **Session State Management** - Centralized state restoration
2. **Modular UI Components** - Separate rendering functions
3. **Error Handling** - Graceful fallbacks and user feedback
4. **Progressive Enhancement** - Features unlock based on state
5. **Database Persistence** - State survives page refreshes
6. **File Processing Pipeline** - Step-by-step document processing
7. **Multi-mode Support** - RAG, Graph RAG, and combined modes

## 🔗 Dependencies & Integration

- **Streamlit** - UI framework
- **LangChain** - Document processing and RAG
- **FAISS** - Vector database
- **NLTK** - Text processing for evaluation
- **SQLite** - State persistence
- **Sentence Transformers** - Embeddings
- **PyVis** - Graph visualization

## 📝 Configuration Management

- **Chunking Parameters** - User-configurable via sliders
- **RAG Modes** - Selectable via sidebar
- **Search Modes** - Vector/Hybrid options
- **Evaluation Modes** - Toggle for chunking analysis
- **Session Persistence** - Automatic state restoration

---

*Generated on: $(date)*
*Total files analyzed: 15+*
*Main functions documented: 25+*
