# 📄 Document Processing Flow - Updated Version

## 🎯 Tổng quan

`document_processing()` là hàm trung tâm xử lý tài liệu đã upload, chịu trách nhiệm chuyển đổi từ raw files thành structured data sẵn sàng cho RAG/Q&A. **Version này đã được cập nhật với UI improvements và logic optimization.**

## 🔄 Flow Diagram (Updated)

```
document_processing()
├── 1. Input Validation & Normalization
├── 2. File Size Check  
├── 3. Session State Initialization
├── 4. Processing Pipeline (by RAG mode)
│   ├── RAG Mode: Ingest → Embed
│   ├── Graph RAG: Ingest → Embed → Extract Triples → Build Graph
│   └── RAG, Graph RAG: Combined flow
├── 5. Hybrid Retriever Build (with UI feedback)
├── 6. Database Persistence (with UI feedback)
├── 7. Vector Store Save
└── 8. Cleanup & Rerun
```

---

## 📋 Chi tiết từng bước (Updated)

### 🔧 Bước 1: Input Validation & Normalization

```python
def _normalize_uploaded_files(uploaded_files):
    if not uploaded_files:
        return []
    return uploaded_files if isinstance(uploaded_files, list) else [uploaded_files]
```

**Chức năng:**
- Chuẩn hóa input thành List[UploadedFile]
- Handle cả single file và multiple files
- Return empty list nếu không có file

---

### ⚖️ Bước 2: File Size Validation

```python
uploaded_files = _normalize_uploaded_files(uploaded_file)
if uploaded_files and st.session_state.rag_mode["name"] is None:
    total_size_mb = sum([(f.size or 0) for f in uploaded_files]) / (1024 * 1024)
    
    if total_size_mb > 100:
        st.error(f"❌ Tổng dung lượng file quá lớn ({total_size_mb:.2f}MB > 100MB)")
        return
```

**Chức năng:**
- Kiểm tra tổng dung lượng files
- Prevent oversized uploads
- Early return nếu quá giới hạn

---

### 🧠 Bước 3: Session State Initialization

```python
st.session_state.rag_mode["name"] = rag_mode
st.session_state.rag_mode["step"] = []
st.session_state.uploaded_file_name = [f.name for f in uploaded_files]
st.session_state.graph_triples = []
st.session_state.documents = []
st.session_state.document_meta = None
st.session_state.is_processing = True
```

**Chức năng:**
- Reset và setup session state cho processing
- Enable processing flag
- Store file names và mode

---

### 🏭 Bước 4: Processing Pipeline (Updated Logic)

#### **Condition Check:**
```python
if uploaded_files and st.session_state.rag_mode["name"] is None:
```

#### **Processing Context:**
```python
with st.status("🔄 Đang xử lý tài liệu...", expanded=True):
```

---

### 📊 Mode-specific Processing Flows (Updated)

#### **🔹 Mode 1: RAG (Simple Retrieval)**

```python
if rag_mode == "RAG":
    documents = ingest_uploaded_files(1, 2, uploaded_files, chunk_size, chunk_overlap)
    _ =         _do_step_embedding(2, 2, documents, retrieval_k)
```

**Flow:**
1. **Step 1/2**: `ingest_uploaded_files()`
   - Load PDF/Word files
   - Chunk với RecursiveCharacterTextSplitter
   - Add metadata (source, file_type, chunk_index)
   - **Note**: Documents được lưu trong `ingest_uploaded_files()` function

2. **Step 2/2**: `_do_step_embedding()`
   - Create vector embeddings
   - Build FAISS index
   - Setup retriever
   - Store trong session state

**🔄 Key Change**: 
- **Removed**: `st.session_state.documents = documents` (đã được move vào `ingest_uploaded_files()`)

---

#### **🔹 Mode 2: Graph RAG (Knowledge Graph)**

```python
elif rag_mode == "Graph RAG":
    documents = ingest_uploaded_files(1, 4, uploaded_files, chunk_size, chunk_overlap)
    _ =         _do_step_embedding(2, 4, documents, retrieval_k)
    triples =   _do_step_extract_triples(3, 4, documents)
    _ =         _do_step_build_graph(4, 4, triples)
```

**Flow:**
1. **Step 1/4**: `ingest_uploaded_files()` - Same as RAG
2. **Step 2/4**: `_do_step_embedding()` - Same as RAG
3. **Step 3/4**: `_do_step_extract_triples()` - Extract entities & relationships
4. **Step 4/4**: `_do_step_build_graph()` - Build and save knowledge graph

**🔄 Key Change**: 
- **Removed**: `st.session_state.documents = documents` (đã được move vào `ingest_uploaded_files()`)

---

#### **🔹 Mode 3: RAG, Graph RAG (Combined)**

```python
else:  # "RAG, Graph RAG"
    documents = ingest_uploaded_files(1, 4, uploaded_files, chunk_size, chunk_overlap)
    _ =         _do_step_embedding(2, 4, documents, retrieval_k)
    triples =   _do_step_extract_triples(3, 4, documents)
    _ =         _do_step_build_graph(4, 4, triples)
```

**Flow:** Same as Graph RAG (4 steps)

**🔄 Key Change**: 
- **Removed**: `st.session_state.documents = documents` (đã được move vào `ingest_uploaded_files()`)

---

### 🔗 Bước 5: Hybrid Retriever Build (Updated with UI)

```python
# Build Hybrid retriever once (for chat "Hybrid" mode)
# Use wider candidate pools than top_k for better recall.
step_build_hybird = st.empty()
step_build_hybird.write(f"Xây dựng Hybrid retriever...")
k = int(retrieval_k) if retrieval_k else 4
try:
    st.session_state.hybrid_retriever = HybridRetriever(
        documents=documents,
        embedder=Config.get_embedder(),
        dense_k=max(30, k * 3),
        sparse_k=max(30, k * 3),
        rerank_k=max(30, k * 6),
        top_k=k,
        alpha=0.6,
        use_rerank=False,
    )
except Exception:
    # Không để lỗi build hybrid làm hỏng flow ingest
    st.session_state.hybrid_retriever = None
step_build_hybird.success(f"**Xây dựng Hybrid retriever thành công**")
```

**🔄 New Features:**
- **UI Feedback**: `step_build_hybird` status container
- **Progress Message**: "Xây dựng Hybrid retriever..."
- **Success Message**: "Xây dựng Hybrid retriever thành công"
- **Error Handling**: Graceful fallback với try-catch

---

### 💾 Bước 6: Database Persistence (Updated with UI)

```python
# Lưu vào database
step_save_database = st.empty()
step_save_database.write(f"Lưu vào database...")
save_retriever_state(st.session_state.session_id, rag_mode, retrieval_k, chunk_size, chunk_overlap)
save_document_state_full(
    st.session_state.session_id,
    st.session_state.uploaded_file_name,
    rag_mode,
    chunk_size,
    chunk_overlap,
    retrieval_k,
    documents,
    st.session_state.rag_mode.get("step", []),
    st.session_state.get("graph_triples", []),
)
st.session_state.document_meta = {
    "session_id": st.session_state.session_id,
    "file_name": st.session_state.uploaded_file_name,
    "mode": rag_mode,
    "chunk_size": chunk_size,
    "chunk_overlap": chunk_overlap,
    "retrieval_k": retrieval_k,
    "documents": documents,
}
vector_dir = os.path.join("vectorstores", st.session_state.session_id)
os.makedirs(vector_dir, exist_ok=True)
st.session_state.vector_db.save_local(vector_dir)
step_save_database.success(f"**Lưu vào database thành công**")
```

**🔄 New Features:**
- **UI Feedback**: `step_save_database` status container
- **Progress Message**: "Lưu vào database..."
- **Success Message**: "Lưu vào database thành công"
- **Combined Operations**: Database + Vector store save trong cùng step

---

### 💾 Bước 7: Vector Store Save (Integrated into Step 6)

Vector store saving đã được tích hợp vào Step 6 để tối ưu UI flow.

---

### 🧹 Bước 8: Cleanup & Rerun

```python
finally:
    st.session_state.is_processing = False
st.rerun()
```

**Process:**
- Reset processing flag
- Hide loading indicators
- Refresh UI với new state

---

## 🔍 Chi tiết Helper Functions (Unchanged)

### `_do_step_embedding()`
- Tạo vector embeddings với FAISS
- Update UI với progress và success messages
- Store vector_db và retriever trong session state

### `_do_step_extract_triples()`
- Extract entities & relationships từ documents
- Return triples list cho graph building
- Update UI với count và processing time

### `_do_step_build_graph()`
- Build networkx graph từ triples
- Save graph to disk
- Store triples trong session state

---

## 🔄 Key Changes in Updated Version

### **1. Document Storage Optimization**
```python
# OLD (trong document_processing.py)
st.session_state.documents = documents

# NEW (trong ingest_uploaded_files.py)
st.session_state.documents = all_docs
```
**Impact**: Documents được lưu ngay sau khi ingest, tránh redundant assignments.

### **2. Enhanced UI Feedback**
```python
# NEW: Hybrid retriever build feedback
step_build_hybird = st.empty()
step_build_hybird.write(f"Xây dựng Hybrid retriever...")
# ... processing ...
step_build_hybird.success(f"**Xây dựng Hybrid retriever thành công**")

# NEW: Database save feedback
step_save_database = st.empty()
step_save_database.write(f"Lưu vào database...")
# ... processing ...
step_save_database.success(f"**Lưu vào database thành công**")
```

**Impact**: User có thể thấy progress rõ ràng hơn cho từng step.

### **3. Removed Redundant Function**
```python
# REMOVED: _do_step_extract_profile()
# Function này không được sử dụng trong flow chính
```

**Impact**: Code cleaner, remove unused function.

### **4. Improved Code Formatting**
```python
# OLD: Standard indentation
_ = _do_step_embedding(2, 2, documents, retrieval_k)

# NEW: Aligned indentation for better readability
_ =         _do_step_embedding(2, 2, documents, retrieval_k)
triples =   _do_step_extract_triples(3, 4, documents)
_ =         _do_step_build_graph(4, 4, triples)
```

**Impact**: Code dễ đọc hơn với aligned indentation.

---

## 📊 Updated Data Flow Summary

### Input → Output Mapping

| Input | Processing | Output | Storage Location |
|-------|------------|--------|-----------------|
| uploaded_files | `_normalize_uploaded_files()` | List[UploadedFile] | Function return |
| chunk_size, chunk_overlap | `ingest_uploaded_files()` | List[Document] | `st.session_state.documents` |
| documents | `_do_step_embedding()` | vector_db, retriever | `st.session_state.vector_db`, `st.session_state.retriever` |
| documents | `_do_step_extract_triples()` | List[Triple] | `st.session_state.graph_triples` |
| triples | `_do_step_build_graph()` | networkx.Graph | Disk file |
| all data | Persistence functions | Database records | SQLite tables |
| vector_db | `save_local()` | Disk files | `vectorstores/{session_id}/` |

### Session State Updates Timeline

| Step | Variable | Set When | Purpose |
|------|----------|----------|---------|
| Start | `rag_mode["name"]` | Line 32 | Processing mode |
| Start | `rag_mode["step"]` | Line 33 | Progress tracking |
| Start | `uploaded_file_name` | Line 34 | File names |
| Start | `graph_triples` | Line 35 | Reset triples |
| Start | `documents` | Line 36 | Reset documents |
| Start | `is_processing` | Line 38 | Loading state |
| Ingest | `documents` | `ingest_uploaded_files()` | Document chunks |
| Embedding | `vector_db` | `_do_step_embedding()` | Search index |
| Embedding | `retriever` | `_do_step_embedding()` | Search object |
| Graph | `graph_triples` | `_do_step_build_graph()` | Knowledge graph |
| End | `document_meta` | Line 98 | UI metadata |
| End | `hybrid_retriever` | Line 67 | Hybrid search |
| End | `is_processing` | Line 112 | Reset loading |

---

## 🎯 Updated UI Flow

### **Step-by-step Progress Display:**

1. **🔄 Đang xử lý tài liệu...** (Main container)
   - **Step 1/X**: 📖 Trích xuất và chunking tài liệu
   - **Step 2/X**: 🔢 Embedding vectors
   - **Step 3/X**: 🧠 Trích xuất thực thể & quan hệ (Graph modes only)
   - **Step 4/X**: 🕸️ Xây dựng graph (Graph modes only)
   - **Xây dựng Hybrid retriever...** → **Xây dựng Hybrid retriever thành công**
   - **Lưu vào database...** → **Lưu vào database thành công**

### **Visual Improvements:**
- **Expanded status container** - User sees all steps
- **Aligned indentation** - Better code readability
- **Success messages** - Clear completion feedback
- **Error handling** - Graceful fallbacks

---

## ⚡ Performance Optimizations

### **1. Reduced Redundant Operations**
- Documents stored once during ingest
- Eliminated duplicate session state assignments

### **2. Improved User Experience**
- Real-time progress feedback
- Clear success/failure indicators
- Better error handling

### **3. Code Maintainability**
- Removed unused functions
- Improved code formatting
- Better separation of concerns

---

## 🔧 Configuration Options (Unchanged)

### **Chunking Parameters:**
- `chunk_size`: 100-2000 characters
- `chunk_overlap`: 0-500 characters
- `retrieval_k`: 1-10 documents

### **Hybrid Retriever:**
- `dense_k`: max(30, k*3) candidates
- `sparse_k`: max(30, k*3) candidates
- `alpha`: 0.6 (dense vs sparse weight)
- `rerank`: Disabled by default

### **File Limits:**
- Maximum size: 100MB total
- Supported formats: PDF, DOCX
- Multiple files supported

---

## 🚀 Summary of Updates

### **Major Improvements:**
1. **Enhanced UI Feedback** - Step-by-step progress indicators
2. **Optimized Document Storage** - Single assignment during ingest
3. **Better Code Organization** - Aligned formatting, removed unused code
4. **Improved Error Handling** - Graceful fallbacks for hybrid retriever
5. **Streamlined Database Operations** - Combined save operations

### **User Experience Benefits:**
- **Clearer Progress** - See exactly what's happening
- **Better Feedback** - Success/failure messages
- **Smoother Flow** - Less redundant operations
- **More Reliable** - Better error handling

### **Developer Benefits:**
- **Cleaner Code** - Better formatting and organization
- **Easier Maintenance** - Removed unused functions
- **Better Debugging** - Clear step indicators
- **Optimized Performance** - Reduced redundant operations

---

*Generated: $(date)*
*Updated Document Processing Flow Analysis*
