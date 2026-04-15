import torch
torch.classes.__path__ = []

import streamlit as st                                               # tạo web UI
from langchain_community.document_loaders import PDFPlumberLoader    # đọc nội dung file PDF
from langchain_text_splitters import RecursiveCharacterTextSplitter  # chia text thành các đoạn nhỏ
from langchain_huggingface import HuggingFaceEmbeddings              # biến text -> vector
from langchain_community.vectorstores import FAISS                   # lưu vector và tìm kiếm similarity
from langchain_ollama import OllamaLLM                               # gọi LLM chạy local
import time
import datetime
import tempfile
import os
import re

# ==================== HELPER FUNCTIONS: CITATION/SOURCE TRACKING ====================

# Stopwords tiếng Việt + tiếng Anh phổ biến (dùng để lọc từ khóa)
_STOPWORDS = {
    'là', 'và', 'của', 'có', 'trong', 'cho', 'được', 'với', 'này', 'các',
    'một', 'những', 'không', 'đã', 'về', 'từ', 'theo', 'đến', 'hay', 'như',
    'khi', 'tại', 'bởi', 'để', 'nếu', 'thì', 'mà', 'vì', 'sẽ', 'đó',
    'cũng', 'do', 'nào', 'ra', 'lại', 'rất', 'hơn', 'nhất', 'gì', 'ai',
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'shall', 'can', 'need', 'ought', 'used',
    'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as',
    'into', 'through', 'before', 'after', 'above', 'below', 'between',
    'out', 'off', 'over', 'under', 'again', 'then', 'once', 'here',
    'there', 'when', 'where', 'why', 'how', 'all', 'each', 'every',
    'both', 'few', 'more', 'most', 'other', 'some', 'no', 'nor', 'not',
    'only', 'same', 'so', 'than', 'too', 'very', 'and', 'but', 'or',
    'if', 'what', 'which', 'who', 'this', 'that', 'these', 'those',
    'i', 'me', 'my', 'we', 'our', 'you', 'your', 'he', 'him', 'his',
    'she', 'her', 'it', 'its', 'they', 'them', 'their',
}

def extract_keywords(question: str) -> list:
    """Tách từ khóa từ câu hỏi, loại bỏ stopwords và từ quá ngắn."""
    words = re.findall(r'[\w]+', question.lower())
    return [w for w in words if w not in _STOPWORDS and len(w) >= 2]

def highlight_text(text: str, keywords: list) -> str:
    """Highlight các từ khóa trong text bằng thẻ <mark class='kw-highlight'>."""
    if not keywords:
        # Chỉ escape HTML, không highlight
        return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    # Escape HTML trước để tránh XSS
    safe = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    for kw in keywords:
        pattern = re.compile(re.escape(kw), re.IGNORECASE)
        safe = pattern.sub(
            lambda m: f'<mark class="kw-highlight">{m.group()}</mark>', safe
        )
    return safe

def enrich_chunk_metadata(documents: list) -> list:
    """Gán chunk_index (đếm theo từng trang) cho mỗi chunk sau khi split."""
    page_counters: dict = {}
    for doc in documents:
        page = doc.metadata.get('page', 0)
        page_counters[page] = page_counters.get(page, 0) + 1
        doc.metadata['chunk_index'] = page_counters[page]
    return documents

def render_sources_ui(sources: list, keywords: list):
    """Render expandable source cards với page badge, chunk index và keyword highlight."""
    if not sources:
        return
    with st.expander(f"📄 Nguồn trích dẫn ({len(sources)} đoạn văn)", expanded=False):
        for i, src in enumerate(sources, 1):
            page_num   = src.get('page', 0) + 1          # 0-indexed → 1-indexed
            chunk_idx  = src.get('chunk_index', '—')
            content    = src.get('content', '')
            char_count = len(content)
            body       = highlight_text(content, keywords)
            st.markdown(f"""
            <div class="source-card-enhanced">
                <div class="source-header">
                    <span class="source-title">📌 Nguồn {i}</span>
                    <div class="source-badges">
                        <span class="page-badge">📄 Trang&nbsp;{page_num}</span>
                        <span class="chunk-badge">🧩 Chunk&nbsp;{chunk_idx}</span>
                        <span class="len-badge">📏 {char_count}&nbsp;ký&nbsp;tự</span>
                    </div>
                </div>
                <div class="source-content">{body}</div>
            </div>
            """, unsafe_allow_html=True)


st.set_page_config(
    page_title="SmartDoc AI",
    page_icon=":material/description:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== SESSION STATE INITIALIZATION ====================
if "chat_history_ui" not in st.session_state:
    st.session_state.chat_history_ui = []

if "retriever" not in st.session_state:
    st.session_state.retriever = None

if "vector_db" not in st.session_state:
    st.session_state.vector_db = None

if "uploaded_file_name" not in st.session_state:
    st.session_state.uploaded_file_name = None

if "document_chunks" not in st.session_state:
    st.session_state.document_chunks = 0

# ==================== 5.1 UI/UX DESIGN ====================
# ==================== 5.1.1 COLOR PALETTE & CUSTOM CSS ====================

st.markdown("""
<style>
    /* ============== GLOBAL STYLES ============== */
    * {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }

    .stApp {
        background-color: #F8F9FA;
        color: #212529;
    }

    hr {
        border: none !important;
        border-top: 1px solid #E3E6EB !important;
        margin: 0.75rem 0 !important;
    }

    /* ============== SIDEBAR STYLING (#2C2F33) ============== */
    [data-testid="stSidebar"] {
        background-color: #2C2F33;
        background-image: linear-gradient(135deg, #2C2F33 0%, #1a1d20 100%);
    }

    [data-testid="stSidebarUserContent"] {
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        padding-left: 1.25rem !important;
        padding-right: 1.25rem !important;
    }

    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] p {
        color: #FFFFFF !important;
    }

    [data-testid="stSidebar"] .stInfo {
        background-color: rgba(0, 123, 255, 0.1) !important;
        border-left: 4px solid #007BFF !important;
        border-radius: 0.5rem;
        padding: 0.75rem !important;
    }

    [data-testid="stSidebar"] .stInfo p {
        color: #FFFFFF !important;
        margin: 0 !important;
    }

    /* ============== BUTTON STYLING ============== */
    .stButton > button {
        background-color: #007BFF;
        color: white;
        border-radius: 8px;
        border: none;
        font-weight: 600;
        padding: 0.6rem 1.2rem;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(0, 123, 255, 0.2);
    }

    .stButton > button:hover {
        background-color: #0056b3;
        box-shadow: 0 4px 12px rgba(0, 123, 255, 0.4);
        transform: translateY(-2px);
    }

    .stButton > button:active {
        transform: translateY(0);
    }

    /* Danger buttons */
    .danger-btn {
        background-color: #DC3545 !important;
    }

    .danger-btn:hover {
        background-color: #C82333 !important;
        box-shadow: 0 4px 12px rgba(220, 53, 69, 0.4) !important;
    }

    /* ============== FILE UPLOADER ============== */
    [data-testid="stFileUploader"] {
        border: 2px dashed #FFC107 !important;
        padding: 2rem !important;
        border-radius: 12px !important;
        background-color: #FFFBF0 !important;
        transition: all 0.3s ease;
    }

    [data-testid="stFileUploader"]:hover {
        border-color: #FF9800 !important;
        background-color: #FFF8E1 !important;
        box-shadow: 0 4px 12px rgba(255, 152, 0, 0.1);
    }

    /* ============== FORM & INPUT ELEMENTS ============== */
    .stTextArea textarea {
        min-height: 140px !important;
        border-radius: 10px !important;
        padding: 14px !important;
        border: 1.5px solid #E3E6EB !important;
        background-color: #FFFFFF !important;
        color: #212529 !important;
        font-size: 14px !important;
        transition: all 0.3s ease;
    }

    .stTextArea textarea:focus {
        border-color: #007BFF !important;
        box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1) !important;
    }

    .stNumberInput input {
        border-radius: 8px !important;
        border: 1.5px solid #E3E6EB !important;
    }

    .stNumberInput input:focus {
        border-color: #007BFF !important;
    }

    /* ============== CARDS & CONTAINERS ============== */
    .card {
        background-color: #FFFFFF;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
        border: 1px solid #E3E6EB;
        margin: 0.5rem 0;
        transition: all 0.3s ease;
    }

    .card:hover {
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
        border-color: #DEE2E6;
    }

    .answer-card {
        background-color: #FFFFFF;
        padding: 20px;
        border-radius: 12px;
        border-left: 5px solid #007BFF;
        box-shadow: 0 2px 12px rgba(0, 123, 255, 0.08);
        color: #212529;
        margin: 0.5rem 0;
    }

    .source-card {
        background-color: #F0F7FF;
        padding: 15px;
        border-radius: 10px;
        border-left: 4px solid #28A745;
        margin: 0.3rem 0;
        color: #212529;
        font-size: 13px;
    }

    .info-box {
        background-color: #E7F3FF;
        border-left: 4px solid #007BFF;
        padding: 12px 16px;
        border-radius: 6px;
        margin: 0.75rem 0;
    }

    /* ============== STATUS & ALERT MESSAGES ============== */
    .stAlert {
        border-radius: 10px !important;
        border: none !important;
        padding: 1rem !important;
    }

    .stSuccess {
        background-color: #D4EDDA !important;
        color: #155724 !important;
    }

    .stError {
        background-color: #F8D7DA !important;
        color: #721C24 !important;
    }

    .stWarning {
        background-color: #FFF3CD !important;
        color: #856404 !important;
    }

    .stInfo {
        background-color: #D1ECF1 !important;
        color: #0C5460 !important;
    }

    /* ============== HEADERS & TEXT ============== */
    h1 {
        color: #212529 !important;
        margin-bottom: 0.5rem !important;
        font-weight: 700 !important;
        font-size: 2.5rem !important;
    }

    h2 {
        color: #212529 !important;
        margin-top: 0.75rem !important;
        margin-bottom: 0.5rem !important;
        font-weight: 700 !important;
        border-bottom: 2px solid #E3E6EB;
        padding-bottom: 0.5rem;
    }

    h3 {
        color: #212529 !important;
        margin-top: 0.5rem !important;
        margin-bottom: 0.5rem !important;
        font-weight: 600 !important;
    }

    /* ============== CHAT MESSAGES ============== */
    .stChatMessage {
        padding: 0.75rem !important;
        background-color: #FFFFFF !important;
        border-radius: 12px !important;
        margin: 0.4rem 0 !important;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04) !important;
    }

    /* ============== METRICS ============== */
    .metric-badge {
        display: inline-block;
        background-color: #007BFF;
        color: white;
        padding: 0.4rem 0.8rem;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        margin: 0.25rem 0.25rem 0.25rem 0;
    }

    /* ============== ANIMATIONS ============== */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }

    .fade-in {
        animation: fadeIn 0.3s ease;
    }

    .pulse {
        animation: pulse 2s ease-in-out infinite;
    }

    /* ============== UTILITY CLASSES ============== */
    .divider-line {
        border: none;
        border-top: 1px solid #E3E6EB;
        margin: 1.5rem 0;
    }

    .text-muted {
        color: #6C757D;
        font-size: 0.9rem;
    }

    .text-success {
        color: #28A745;
        font-weight: 600;
    }

    .text-danger {
        color: #DC3545;
        font-weight: 600;
    }

    /* ============== CITATION / SOURCE TRACKING ============== */
    mark.kw-highlight {
        background-color: #FFF176;
        color: #212529;
        padding: 1px 4px;
        border-radius: 3px;
        font-weight: 600;
        box-shadow: 0 1px 2px rgba(255,241,118,0.5);
    }

    .source-card-enhanced {
        background-color: #F8FAFC;
        padding: 14px 16px;
        border-radius: 10px;
        border-left: 4px solid #28A745;
        margin: 0.55rem 0;
        color: #212529;
        transition: box-shadow 0.25s ease, border-left-color 0.25s ease;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    }

    .source-card-enhanced:hover {
        box-shadow: 0 4px 14px rgba(40,167,69,0.14);
        border-left-color: #1E7E34;
    }

    .source-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
        flex-wrap: wrap;
        gap: 6px;
    }

    .source-title {
        font-weight: 700;
        font-size: 0.95rem;
        color: #212529;
    }

    .source-badges {
        display: flex;
        gap: 6px;
        flex-wrap: wrap;
    }

    .page-badge {
        display: inline-flex;
        align-items: center;
        background: linear-gradient(135deg, #007BFF 0%, #0056b3 100%);
        color: white;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.3px;
    }

    .chunk-badge {
        display: inline-flex;
        align-items: center;
        background: linear-gradient(135deg, #28A745 0%, #1E7E34 100%);
        color: white;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
    }

    .len-badge {
        display: inline-flex;
        align-items: center;
        background: linear-gradient(135deg, #6C757D 0%, #495057 100%);
        color: white;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
    }

    .source-content {
        font-size: 0.875rem;
        line-height: 1.75;
        color: #343A40;
        padding: 10px 12px;
        background-color: #FFFFFF;
        border-radius: 6px;
        border: 1px solid #E9ECEF;
        max-height: 280px;
        overflow-y: auto;
        word-wrap: break-word;
        white-space: pre-wrap;
    }
</style>
""", unsafe_allow_html=True)

# ==================== 5.1.2 SIDEBAR LAYOUT ====================
with st.sidebar:
    # ========== HEADER ==========
    st.markdown("""
    <div style="text-align: center; margin-bottom: 1.25rem; padding-bottom: 1rem; border-bottom: 1px solid rgba(255,255,255,0.1);">
        <h1 style="font-size: 1.6rem; margin: 0; color: #FFFFFF; font-weight: 700;">📚 SmartDoc</h1>
        <p style="color: #FFFFFF; opacity: 0.7; margin: 0.25rem 0 0 0; font-size: 0.85rem; letter-spacing: 0.5px;">AI RAG System</p>
    </div>
    """, unsafe_allow_html=True)
    
    # ========== QUICK GUIDE ==========
    st.subheader("🎯 Quick Guide", divider=False)
    st.markdown("""
    <div style="background-color: rgba(0,123,255,0.1); padding: 0.75rem; border-radius: 8px; border-left: 3px solid #007BFF; font-size: 0.9rem; line-height: 1.6;">
    1️⃣ <strong>Settings</strong> - Chunk config<br/>
    2️⃣ <strong>Upload</strong> - PDF file<br/>
    3️⃣ <strong>Ask</strong> - Ask questions<br/>
    4️⃣ <strong>Get</strong> - Get answers
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    # ========== SYSTEM INFO ==========
    st.subheader("⚙️ System Info", divider=False)
    cols = st.columns(2)
    with cols[0]:
        st.metric("Format", "PDF", label_visibility="collapsed")
    with cols[1]:
        st.metric("Max Size", "50MB", label_visibility="collapsed")
    
    cols = st.columns(2)
    with cols[0]:
        st.metric("Language", "2+", label_visibility="collapsed")
    with cols[1]:
        chunks_display = st.session_state.document_chunks if st.session_state.document_chunks > 0 else "—"
        st.metric("Chunks", chunks_display, label_visibility="collapsed")
    
    st.divider()
    
    # ========== MODEL CONFIG ==========
    st.subheader("🤖 Models", divider=False)
    st.markdown("""
    <div style="font-size: 0.9rem; line-height: 1.8; color: #FFFFFF;">
    <strong>LLM:</strong> qwen2.5:7b<br/>
    <strong>Embedding:</strong> MPNet (768-dim)<br/>
    <strong>Vector DB:</strong> FAISS
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    # ========== ACTIONS ==========
    if st.session_state.retriever is not None:
        st.subheader("📋 Manage Data", divider=False)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Clear Chat", use_container_width=True, key="clear_chat"):
                st.session_state.chat_history_ui = []
                st.toast("✓ Chat cleared!")
                st.rerun()
        with col2:
            if st.button("🗑️ Clear All", use_container_width=True, key="clear_all"):
                st.session_state.retriever = None
                st.session_state.vector_db = None
                st.session_state.document_chunks = 0
                st.session_state.uploaded_file_name = None
                st.session_state.chat_history_ui = []
                st.toast("✓ All data cleared!")
                st.rerun()
        st.divider()
    
    # ========== FOOTER ==========
    st.markdown("""
    <div style="text-align: center; color: #FFFFFF; opacity: 0.5; font-size: 0.7rem; margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid rgba(255,255,255,0.1);">
        <p style="margin: 0.15rem 0;">© 2026 SmartDoc AI</p>
        <p style="margin: 0.15rem 0;">OSSD • Saigon University</p>
    </div>
    """, unsafe_allow_html=True)

# ==================== MAIN AREA LAYOUT ====================

# ========== HEADER SECTION ==========
st.markdown("""
<div style="text-align: center; margin-bottom: 1.5rem;">
    <h1 style="margin: 0; color: #212529; font-size: 2.2rem;">🚀 SmartDoc AI</h1>
    <p style="margin: 0.3rem 0 0 0; color: #6C757D; font-size: 1rem;">Intelligent Document Q&A System</p>
</div>
""", unsafe_allow_html=True)

main_col = st.container()

# ========== CHUNKING CONFIGURATION (BEFORE UPLOAD) ==========
with main_col:
    with st.expander("⚙️ **Cấu hình Chunking** (Bước 1 - Thiết lập trước)", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            chunk_size = st.slider(
                "Chunk Size",
                min_value=100,
                max_value=2000,
                value=500,
                step=50,
                help="Kích thước mỗi đoạn văn bản",
                label_visibility="collapsed"
            )
            st.caption(f"📐 Size: {chunk_size} ký tự")
        
        with col2:
            chunk_overlap = st.slider(
                "Chunk Overlap",
                min_value=0,
                max_value=500,
                value=50,
                step=10,
                help="Overlap giữa chunks",
                label_visibility="collapsed"
            )
            st.caption(f"🔗 Overlap: {chunk_overlap} ký tự")
        
        with col3:
            retrieval_k = st.slider(
                "Top-K Nguồn",
                min_value=1,
                max_value=10,
                value=3,
                step=1,
                help="Số chunks truy xuất từ FAISS (dùng cho cả LLM và hiển thị nguồn)",
                label_visibility="collapsed"
            )
            st.caption(f"📚 Top-K: {retrieval_k} nguồn")

# ========== DOCUMENT UPLOAD SECTION ==========
with main_col:
    st.subheader("📤 Upload File PDF (Bước 2)", divider=True)
    
    col_upload, col_status = st.columns([3, 1])
    
    with col_upload:
        uploaded_file = st.file_uploader(
            "Chọn file PDF",
            type=["pdf"],
            label_visibility="collapsed"
        )
    
    with col_status:
        if st.session_state.retriever is not None:
            st.markdown("""
            <div style="background-color: #D4EDDA; padding: 0.5rem 0.75rem; border-radius: 6px; text-align: center;">
                <p style="margin: 0; color: #155724; font-weight: 600; font-size: 0.85rem;">✓ Sẵn sàng</p>
            </div>
            """, unsafe_allow_html=True)

# ========== DOCUMENT STATUS ==========
if st.session_state.retriever is not None:
    with main_col:
        st.markdown("""
        <div style="background-color: #E7F3FF; border-left: 4px solid #007BFF; padding: 0.75rem; border-radius: 8px; margin: 0.5rem 0;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <p style="margin: 0; color: #0C5460; font-weight: 600; font-size: 0.95rem;">📄 Tài liệu: <strong>""" + 
                    str(st.session_state.document_chunks) + """ chunks</strong></p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ==================== 3.2.1 DOCUMENT PROCESSING FLOW ====================
if uploaded_file and st.session_state.retriever is None:
    file_size_mb = uploaded_file.size / (1024 * 1024)
    
    if file_size_mb > 50:
        st.error("""
        :material/error: **File quá lớn!**  
        Kích thước file: {:.2f}MB > 50MB  
        Vui lòng chọn file nhỏ hơn.
        """.format(file_size_mb))
    
    else:
        # Save temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.getbuffer())
            temp_path = tmp.name
        
        st.session_state.uploaded_file_name = uploaded_file.name
        
        # Processing with status
        with st.status("🔄 Đang phân tích tài liệu...", expanded=True) as status:
            try:
                # ========== STEP 1: LOAD PDF ==========
                step1 = st.empty()
                start_time = time.time()
                step1.write("📖 Bước 1/3: Trích xuất văn bản từ PDF...")
                
                loader = PDFPlumberLoader(temp_path)
                docs = loader.load()
                
                elapsed = round(time.time() - start_time, 2)
                step1.success(f"✓ Trích xuất xong: {len(docs)} trang trong {elapsed}s")
                
                # ========== STEP 2: CHUNKING ==========
                step2 = st.empty()
                start_time = time.time()
                step2.write("✂️ Bước 2/3: Chia nhỏ văn bản thành chunks...")
                
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=int(chunk_size),
                    chunk_overlap=int(chunk_overlap)
                )
                documents = text_splitter.split_documents(docs)
                # ── Citation tracking: gán chunk_index theo từng trang ──
                documents = enrich_chunk_metadata(documents)

                elapsed = round(time.time() - start_time, 2)
                step2.success(f"✓ Chunking xong: {len(documents)} chunks trong {elapsed}s")
                st.session_state.document_chunks = len(documents)
                
                # ========== STEP 3: EMBEDDING & INDEXING ==========
                step3 = st.empty()
                start_time = time.time()
                step3.write("🔢 Bước 3/3: Tạo vector embeddings...")
                
                embedder = HuggingFaceEmbeddings(
                    model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
                    model_kwargs={'device': 'cpu'},
                    encode_kwargs={'normalize_embeddings': True}
                )
                
                vector_db = FAISS.from_documents(documents, embedder)
                st.session_state.vector_db = vector_db
                st.session_state.retriever = vector_db.as_retriever(
                    search_type="similarity",
                    search_kwargs={"k": int(retrieval_k)}
                )
                
                elapsed = round(time.time() - start_time, 2)
                step3.success(f"✓ Embedding xong: 768-dim vectors trong {elapsed}s")
                
                status.update(
                    label="✅ PDF đã xử lý thành công!",
                    state="complete",
                    expanded=False
                )
                st.success("""
                :material/check_circle: **Tài liệu sẵn sàng!**  
                Bạn có thể bắt đầu đặt câu hỏi được rồi.
                """)
                
            except Exception as e:
                status.update(label="❌ Xảy ra lỗi!", state="error", expanded=True)
                st.error(f"""
                :material/error: **Lỗi xử lý tài liệu**
                ```
                {str(e)}
                ```
                """)
            
            finally:
                # Clean up temp file
                try:
                    os.remove(temp_path)
                except:
                    pass

# ==================== CHAT SECTION ====================
if st.session_state.retriever is not None:
    st.divider()
    
    # ========== CHAT HISTORY ==========
    st.subheader("💬 Lịch sử hội thoại (Bước 3)", divider=True)
    
    if len(st.session_state.chat_history_ui) == 0:
        st.markdown("""
        <div style="text-align: center; padding: 1.5rem; color: #6C757D;">
            <p style="font-size: 1rem; margin: 0; opacity: 0.7;">Chưa có cuộc hội thoại</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        for i, msg in enumerate(st.session_state.chat_history_ui):
            if msg["role"] == "user":
                with st.chat_message("user", avatar="👤"):
                    st.markdown(msg["content"])
                    st.caption(f"⏰ {msg['timestamp']}", unsafe_allow_html=False)
            else:
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(msg["content"])
                    response_time = msg.get('response_time', 0)
                    st.caption(f"⏰ {msg['timestamp']} • ⚡ {response_time}s")
                    # ── Citation tracking: hiển thị lại sources trong history ──
                    _hist_sources   = msg.get('sources', [])
                    _hist_keywords  = msg.get('keywords', [])
                    if _hist_sources:
                        render_sources_ui(_hist_sources, _hist_keywords)
    
    st.divider()
    
    # ========== QUESTION INPUT ==========
    st.subheader("❓ Đặt câu hỏi (Bước 4)", divider=True)
    
    with st.form(key="question_form", border=False):
        question = st.text_area(
            "Nhập câu hỏi:",
            placeholder="Ví dụ: Các bước cài đặt là gì?",
            height=100,
            label_visibility="collapsed"
        )
        
        col1, col2 = st.columns([4, 1])
        with col2:
            submit_question = st.form_submit_button(
                "📤 Gửi",
                use_container_width=True,
                type="primary"
            )
    
    # ========== PROCESS QUESTION ==========
    if submit_question:
        if not question.strip():
            st.error("⚠️ Vui lòng nhập câu hỏi!")
        else:
            with st.spinner("🔍 Đang xử lý..."):
                try:
                    # Save user message
                    st.session_state.chat_history_ui.append({
                        "role": "user",
                        "content": question,
                        "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
                        "response_time": None
                    })
                    
                    start_time = time.time()
                    
                    # Configure LLM
                    llm = OllamaLLM(
                        model="qwen2.5:7b",
                        temperature=0.7,
                        top_p=0.9,
                        repeat_penalty=1.1,
                    )
                    
                    # Truy xuất tài liệu liên quan (dùng retrieval_k cho cả LLM và hiển thị)
                    relevant_docs = st.session_state.retriever.invoke(question)
                    context = "\n---\n".join([doc.page_content for doc in relevant_docs])
                    
                    # Get chat history for context
                    chat_history = st.session_state.chat_history_ui[-6:]
                    history_text = "\n".join([
                        f"User: {m['content']}" if m["role"] == "user" else f"AI: {m['content']}"
                        for m in chat_history[:-1]
                    ])
                    
                    # Detect language
                    vietnamese_chars = 'aăâdđeêiôơuưỳỵỷỹý'
                    is_vietnamese = any(char in question.lower() for char in vietnamese_chars)
                    
                    # Generate prompt
                    if is_vietnamese:
                        prompt_template = f"""Bạn là trợ lý AI thông minh, chuyên trả lời câu hỏi dựa trên tài liệu.

HƯỚNG DẪN:
- Chỉ sử dụng thông tin từ "Ngữ cảnh" để trả lời
- Kết hợp "Lịch sử hội thoại" để hiểu câu hỏi tiếp theo
- Nếu không tìm thấy câu trả lời, nói: "Tôi không có thông tin về điều này"
- Trả lời bằng tiếng Việt, rõ ràng và ngắn gọn

LỊ SỬ HỘI THOẠI:
{history_text}

NGỮCẢNH:
{context}

CẦU HỎI:
{question}

TRẢ LỜI:"""
                    else:
                        prompt_template = f"""You are an intelligent AI assistant specialized in answering questions based on documents.

INSTRUCTIONS:
- Only use information from the "CONTEXT" provided
- Use "CHAT HISTORY" to understand follow-up questions
- If the answer is not in the context, say: "I don't have that information"
- Be concise and accurate

CHAT HISTORY:
{history_text}

CONTEXT:
{context}

QUESTION:
{question}

ANSWER:"""
                    
                    # Get LLM response
                    response = llm.invoke(prompt_template)
                    elapsed_time = round(time.time() - start_time, 2)
                    
                    # ── Citation tracking: chuẩn bị sources data ──
                    sources_data = [
                        {
                            "page":        doc.metadata.get('page', 0),
                            "chunk_index": doc.metadata.get('chunk_index', '—'),
                            "content":     doc.page_content,
                        }
                        for doc in relevant_docs
                    ]
                    keywords = extract_keywords(question)

                    # Save assistant message (kèm sources + keywords)
                    st.session_state.chat_history_ui.append({
                        "role":          "ai",
                        "content":       response,
                        "timestamp":     datetime.datetime.now().strftime("%H:%M:%S"),
                        "response_time": elapsed_time,
                        "sources":       sources_data,
                        "keywords":      keywords,
                    })

                    # Display response
                    st.success("✓ Câu trả lời đã được sinh ra!")

                    # Show answer card
                    st.markdown(f"""
                    <div class="answer-card">
                        <p><strong>📝 Câu trả lời:</strong></p>
                        <p>{response}</p>
                        <div style="margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid #E3E6EB;">
                            <span class="text-muted">⚡ {elapsed_time}s • 📚 {len(relevant_docs)} nguồn trích dẫn</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # ── Citation tracking: hiển thị sources nâng cao ──
                    render_sources_ui(sources_data, keywords)
                    
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"""
                    ❌ **Lỗi xử lý**
                    ```
                    {str(e)}
                    ```
                    """)

else:
    st.divider()
    st.markdown("""
    <div style="text-align: center; padding: 2rem; background-color: #F0F7FF; border-radius: 12px; margin: 1rem 0;">
        <p style="font-size: 1.1rem; color: #0C5460; margin: 0 0 0.5rem 0; font-weight: 600;">📤 Tải lên tài liệu để bắt đầu</p>
        <p style="color: #0C5460; margin: 0; font-size: 0.95rem;">Sử dụng mục "Upload File PDF" phía trên</p>
    </div>
    """, unsafe_allow_html=True)