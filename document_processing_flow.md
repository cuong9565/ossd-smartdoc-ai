# 📄 Document Processing Flow - Chi tiết Quy trình Xử lý

## 🎯 Tổng quan

`document_processing()` là hàm trung tâm xử lý tài liệu đã upload, chịu trách nhiệm chuyển đổi từ raw files thành structured data sẵn sàng cho RAG/Q&A.

## 🔄 Flow Diagram

```
document_processing()
├── 1. Input Validation & Normalization
├── 2. File Size Check  
├── 3. Session State Initialization
├── 4. Processing Pipeline (by RAG mode)
│   ├── RAG Mode: Ingest → Embed
│   ├── Graph RAG: Ingest → Embed → Extract Triples → Build Graph
│   └── RAG, Graph RAG: Combined flow
├── 5. Hybrid Retriever Build
├── 6. State Persistence
├── 7. Vector Store Save
└── 8. Cleanup & Rerun
```

---

## 📋 Chi tiết từng bước

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

**Logic:**
- Check if uploaded_files is list or single file
- Convert single file to list with one element
- Ensure consistent data type for downstream processing

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

**Logic:**
- Sum file sizes in MB
- Compare against 100MB limit
- Show error message và exit nếu quá lớn

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

**Các variables được khởi tạo:**
- `rag_mode["name"]` - Set mode được chọn
- `rag_mode["step"]` - Reset processing steps list
- `uploaded_file_name` - Store file names list
- `graph_triples` - Reset triples list
- `documents` - Reset documents list
- `document_meta` - Reset metadata
- `is_processing` - Set True để show loading

---

### 🏭 Bước 4: Processing Pipeline (Main Logic)

#### **Condition Check:**
```python
if uploaded_files and st.session_state.rag_mode["name"] is None:
```
- Chỉ process khi có files VÀ chưa có mode active
- Prevent re-processing khi đã có data

#### **Processing Context:**
```python
with st.status("🔄 Đang xử lý tài liệu...", expanded=True):
```
- Show status container với loading message
- Expanded để user thấy progress

---

### 📊 Mode-specific Processing Flows

#### **🔹 Mode 1: RAG (Simple Retrieval)**

```python
if rag_mode == "RAG":
    documents = ingest_uploaded_files(1, 2, uploaded_files, chunk_size, chunk_overlap)
    _ = _do_step_embedding(2, 2, documents, retrieval_k)
    st.session_state.documents = documents
```

**Flow:**
1. **Step 1/2**: `ingest_uploaded_files()`
   - Load PDF/Word files
   - Chunk với RecursiveCharacterTextSplitter
   - Add metadata (source, file_type, chunk_index)
   - Return List[Document] objects

2. **Step 2/2**: `_do_step_embedding()`
   - Create vector embeddings
   - Build FAISS index
   - Setup retriever
   - Store trong session state

---

#### **🔹 Mode 2: Graph RAG (Knowledge Graph)**

```python
elif rag_mode == "Graph RAG":
    documents = ingest_uploaded_files(1, 4, uploaded_files, chunk_size, chunk_overlap)
    _ = _do_step_embedding(2, 4, documents, retrieval_k)
    triples = _do_step_extract_triples(3, 4, documents)
    _ = _do_step_build_graph(4, 4, triples)
    st.session_state.documents = documents
```

**Flow:**
1. **Step 1/4**: `ingest_uploaded_files()` - Same as RAG
2. **Step 2/4**: `_do_step_embedding()` - Same as RAG
3. **Step 3/4**: `_do_step_extract_triples()`
   - Extract entities & relationships
   - Generate knowledge graph triples
   - Return List[Triple] objects
4. **Step 4/4**: `_do_step_build_graph()`
   - Build networkx graph from triples
   - Save graph to disk
   - Store triples trong session state

---

#### **🔹 Mode 3: RAG, Graph RAG (Combined)**

```python
else:  # "RAG, Graph RAG"
    documents = ingest_uploaded_files(1, 4, uploaded_files, chunk_size, chunk_overlap)
    _ = _do_step_embedding(2, 4, documents, retrieval_k)
    triples = _do_step_extract_triples(3, 4, documents)
    _ = _do_step_build_graph(4, 4, triples)
    st.session_state.documents = documents
```

**Flow:** Same as Graph RAG (4 steps)

---

### 🔍 Chi tiết Helper Functions

#### **`_do_step_embedding()`**

```python
def _do_step_embedding(stepcurr, numstep, documents, retrieval_k):
    step = st.empty()
    step.write(f"🔢 Bước {stepcurr}/{numstep}: Tạo vector embeddings...")
    elapsed, vector_db, retriever = embedding(documents, retrieval_k)
    step.success(f"🔢 Embedding {vector_db.index.ntotal} vector, {vector_db.index.d} chiều trong **{elapsed}s**")
    st.session_state.rag_mode["step"].append(f"🔢 Embedding {vector_db.index.ntotal} vector, {vector_db.index.d} chiều trong **{elapsed}s**")
    st.session_state.vector_db = vector_db
    st.session_state.retriever = retriever
    return None
```

**Process:**
1. Show progress message
2. Call `embedding()` function từ core module
3. Update UI với success message
4. Log step vào session state
5. Store vector_db và retriever

**Return từ `embedding()`:**
- `elapsed` - Processing time
- `vector_db` - FAISS vector database
- `retriever` - Retriever object

---

#### **`_do_step_extract_triples()`**

```python
def _do_step_extract_triples(stepcurr, numstep, documents):
    step = st.empty()
    step.write(f"🧠 Bước {stepcurr}/{numstep}: Trích xuất thực thể & quan hệ...")
    elapsed, triples = extract_triples(documents)
    step.success(f"🧠 Trích xuất {len(triples)} triples trong **{elapsed}s**")
    st.session_state.rag_mode["step"].append(f"🧠 Trích xuất {len(triples)} triples trong **{elapsed}s**")
    return triples
```

**Process:**
1. Show progress message
2. Call `extract_triples()` từ advanced module
3. Update UI với count và time
4. Log step vào session state
5. Return triples list

**Triple Structure:**
- Subject, Predicate, Object relationships
- Extracted từ document chunks
- Used cho knowledge graph construction

---

#### **`_do_step_build_graph()`**

```python
def _do_step_build_graph(stepcurr, numstep, triples):
    step = st.empty()
    step.write(f"🕸️ Bước {stepcurr}/{numstep}: Xây dựng graph...")
    elapsed, graph = build_graph(triples)
    save_graph(graph)
    step.success(f"🕸️ Xây dựng  trong **{elapsed}s**")
    st.session_state.graph_triples = triples
    st.session_state.rag_mode["step"].append(f"🕸️ Xây dựng  trong **{elapsed}s**")
    return None
```

**Process:**
1. Show progress message
2. Call `build_graph()` từ advanced module
3. Save graph với `save_graph()`
4. Update UI với success message
5. Store triples trong session state
6. Log step vào session state

---

### 🔗 Bước 5: Hybrid Retriever Build

```python
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
    st.session_state.hybrid_retriever = None
```

**Chức năng:**
- Build hybrid retriever cho Vector + Sparse search
- Use wider candidate pools cho better recall
- Graceful fallback nếu build fails

**Parameters:**
- `dense_k` - Dense retrieval candidates (max(30, k*3))
- `sparse_k` - Sparse retrieval candidates (max(30, k*3))
- `rerank_k` - Reranking candidates (max(30, k*6))
- `top_k` - Final results (k)
- `alpha` - Weight giữa dense/sparse (0.6)
- `use_rerank` - Cross-encoder reranking (False)

---

### 💾 Bước 6: State Persistence

#### **Retriever State Save:**
```python
save_retriever_state(st.session_state.session_id, rag_mode, retrieval_k, chunk_size, chunk_overlap)
```

**Saves vào `retriever_state` table:**
- session_id
- mode (RAG/Graph RAG)
- retriever_k
- chunk_size
- chunk_overlap

#### **Document State Save:**
```python
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
```

**Saves vào `document_state` table:**
- session_id
- file_name
- mode
- chunk_size, chunk_overlap, retrieval_k
- documents (JSON serialized)
- steps_json (processing steps)
- graph_triples_json (if any)

#### **Document Metadata:**
```python
st.session_state.document_meta = {
    "session_id": st.session_state.session_id,
    "file_name": st.session_state.uploaded_file_name,
    "mode": rag_mode,
    "chunk_size": chunk_size,
    "chunk_overlap": chunk_overlap,
    "retrieval_k": retrieval_k,
    "documents": documents,
}
```

**Metadata cho UI display và internal use**

---

### 💾 Bước 7: Vector Store Persistence

```python
vector_dir = os.path.join("vectorstores", st.session_state.session_id)
os.makedirs(vector_dir, exist_ok=True)
st.session_state.vector_db.save_local(vector_dir)
```

**Process:**
1. Create session-specific directory
2. Save FAISS index to disk
3. Enable persistence across sessions

**Directory Structure:**
```
vectorstores/
└── {session_id}/
    ├── index.faiss
    └── index.pkl
```

---

### 🧹 Bước 8: Cleanup & Rerun

```python
finally:
    st.session_state.is_processing = False
st.rerun()
```

**Cleanup:**
- Reset processing flag
- Hide loading indicators

**Rerun:**
- Refresh UI với new state
- Show processed documents
- Enable chat interface

---

## 📊 Data Flow Summary

### Input → Output Mapping

| Input | Processing | Output |
|-------|------------|--------|
| uploaded_files | `_normalize_uploaded_files()` | List[UploadedFile] |
| chunk_size, chunk_overlap | `ingest_uploaded_files()` | List[Document] |
| documents | `_do_step_embedding()` | vector_db, retriever |
| documents | `_do_step_extract_triples()` | List[Triple] |
| triples | `_do_step_build_graph()` | networkx.Graph |
| all data | Persistence functions | Database records |
| vector_db | `save_local()` | Disk files |

### Session State Updates

| Variable | Set When | Purpose |
|----------|----------|---------|
| `rag_mode["name"]` | Start | Processing mode |
| `rag_mode["step"]` | Each step | Progress tracking |
| `uploaded_file_name` | Start | File names |
| `documents` | After ingest | Document chunks |
| `graph_triples` | After graph | Knowledge graph |
| `document_meta` | End | UI metadata |
| `vector_db` | After embedding | Search index |
| `retriever` | After embedding | Search object |
| `hybrid_retriever` | After pipeline | Hybrid search |
| `is_processing` | Start/End | Loading state |

---

## 🎯 Key Design Patterns

### 1. **Progressive Processing**
- Step-by-step UI updates
- Clear progress indicators
- Graceful error handling

### 2. **Mode-based Architecture**
- Different flows per RAG mode
- Scalable for new modes
- Clear separation of concerns

### 3. **State Persistence**
- Database storage for metadata
- Disk storage for vectors
- Session state for UI

### 4. **Error Resilience**
- Try-catch for hybrid retriever
- Finally block for cleanup
- Validation at multiple levels

### 5. **Resource Management**
- File size limits
- Memory-efficient processing
- Proper cleanup procedures

---

## ⚡ Performance Considerations

### **Chunk Size Impact:**
- Smaller chunks = More vectors = Longer embedding time
- Larger chunks = Fewer vectors = Less granular retrieval
- Trade-off between precision and recall

### **Mode Performance:**
- **RAG**: Fastest (2 steps)
- **Graph RAG**: Slower (4 steps + graph processing)
- **Combined**: Same as Graph RAG

### **Memory Usage:**
- Documents stored in session state
- Vector database in memory
- Graph triples in memory
- Consider large document handling

---

## 🔧 Configuration Options

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

## 🚀 Future Enhancements

### **Potential Improvements:**
1. **Async Processing** - Non-blocking document processing
2. **Progress Callbacks** - Real-time progress updates
3. **Batch Processing** - Handle multiple documents efficiently
4. **Cache Layer** - Avoid re-processing same files
5. **Streaming** - Process large files in chunks
6. **Parallel Processing** - Multi-core utilization

### **Scaling Considerations:**
- Vector database sharding
- Distributed graph processing
- Cloud storage integration
- Load balancing for multiple users

---

*Generated: $(date)*
*Document Processing Flow Analysis*
