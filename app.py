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

st.set_page_config(
    page_title="SmartDoc AI",
    page_icon=":material/description:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Khởi tạo lịch sử hội thoại trong session state
if "chat_history_ui" not in st.session_state:
    st.session_state.chat_history_ui = []

if "retriever" not in st.session_state:
    st.session_state.retriever = None

# ================= 5.1 THIẾT KẾ UI/UX =================

# ================= 5.1.1 COLOR PALETTE & CUSTOM CSS =================
st.markdown("""
<style>
    /* Main Background (#F8F9FA) */
    .stApp {
        background-color: #F8F9FA;
    }

    /* Divider color */
    hr {
        border: 1px solid #FFFFFF !important;
    }

    /* 5.1.2 Layout Structure: Sidebar (#2C2F33) */
    [data-testid="stSidebar"] {
        background-color: #2C2F33;
        color: #FFFFFF;
    }
            
    /* Loại bỏ padding mặc định của container Sidebar */
    [data-testid="stSidebarUserContent"] {
        padding-top: 1rem !important;
        padding-bottom: 3rem !important;
    }
    
    /* Sidebar Text & Headers (#FFFFFF) */
    [data-testid="stSidebar"] .stMarkdown, 
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] p {
        color: #FFFFFF !important;
    }

    /* Primary Color: Buttons (#007BFF) */
    .stButton>button {
        background-color: #007BFF;
        color: white;
        border-radius: 6px;
        border: none;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #0056b3;
        color: white;
    }

    /* Secondary Color: Upload Box Border (#FFC107) */
    [data-testid="stFileUploader"] {
        border: 2px dashed #FFC107;
        padding: 10px;
        border-radius: 10px;
        background-color: #FFFFFF;
    }

    /* Text Color (#212529) */
    .main .stMarkdown, .main p, .main h1, .main h2 {
        color: #212529;
    }

    /* Response Card Style */
    .answer-card {
        background-color: #FFFFFF;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #007BFF;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        color: #212529;
    }

    /* Multiline input styling */
    .stTextArea textarea {
        min-height: 140px;
        border-radius: 12px;
        padding: 14px;
        border: 1px solid #dfe3e8;
        background-color: #ffffff;
        color: #212529;
    }

    .stTextArea {
        margin-bottom: 1rem;
    }

    .stButton>button:focus {
        outline: 2px solid #0056b3;
        box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.25);
    }
</style>
""", unsafe_allow_html=True)

# ================= 5.1.2 SIDEBAR (Bên trái) =================
with st.sidebar:
    st.header(":material/help_outline: Hướng dẫn sử dụng")
    st.write("1. Tải lên file PDF bằng cách kéo thả hoặc click vào khu vực upload.")
    st.write("2. Đợi hệ thống xử lý và phân tích tài liệu.")
    st.write("3. Nhập câu hỏi vào ô tìm kiếm.")
    st.write("4. Xem câu trả lời được sinh ra bởi AI.")
    st.write("5. Có thể đặt nhiều câu hỏi liên tiếp.")

    st.divider()
    
    st.header(":material/settings: Thông tin hệ thống")
    st.info("Định dạng: Chỉ PDF")
    st.info("Kích thước tối đa: 50MB")
    st.info("Ngôn ngữ hỗ trợ: Tiếng Việt, English")

    st.divider()
    
    st.header(":material/memory: Cấu hình Model")
    st.info("LLM Model: **qwen2.5:7b (Ollama)**")
    st.info("Version: **1.0**")
    st.info("Embedding: **paraphrase-multilingual-mpnet-base-v2**")
    
    st.divider()
    st.markdown(
    """
        <div style="text-align: center; color: #FFFFFF; opacity: 0.7; font-size: 0.8rem;">
            RAG System with LLMs © 2026
        </div>
    """, unsafe_allow_html=True)

# ================= MAIN AREA (Chính giữa) =================
# Title và Header
st.title(":material/rocket_launch: SmartDoc AI - RAG System")
st.write("Hệ thống hỏi đáp thông minh dựa trên tài liệu PDF nội bộ.")

# File Upload
st.header(":material/upload_file: Upload file PDF")
uploaded_file = st.file_uploader("Chọn file PDF (Kéo-Thả hoặc Tìm file)", type=["pdf"])

# Cấu hình Chungking
st.subheader(":material/settings: Cấu hình Chunking")

col1, col2 = st.columns(2)

with col1:
    chunk_size = st.number_input(
        "Chunk size",
        min_value=100,
        max_value=2000,
        value=500,
        step=50,
        help="Kích thước mỗi đoạn văn bản"
    )

with col2:
    chunk_overlap = st.number_input(
        "Chunk overlap",
        min_value=0,
        max_value=500,
        value=50,
        step=10,
        help="Số ký tự overlap giữa các chunk"
    )

# ================= 3.2.1 DOCUMENT PROCESSING FLOW =================
if uploaded_file and st.session_state.retriever is None: 
    if uploaded_file.size > 50 * 1024 * 1024: 
        st.error(":material/error: Lỗi: File vượt quá giới hạn 50MB!") # [10]
    else:
        # Lưu file tạm để xử lý
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.getbuffer())
            temp_path = tmp.name

        # Sử dụng st.status để hiển thị tiến trình xử lý
        with st.status("Đang phân tích tài liệu...", expanded=True) as status:
            # ========== Loading PDF ==========
            start_time = time.time()
            loading_text = st.empty()
            loading_text.write("Đang trích xuất văn bản...")
            # Xử lý
            loader = PDFPlumberLoader(temp_path)
            docs = loader.load()
            # Ghi kết quả
            end_time = time.time()
            loading_text.success(f"Đã trích xuất văn bản xong trong {round(end_time - start_time, 2)} giây")            
            
            # ========== Chunking ==========
            start_time = time.time()
            chunking_text = st.empty()
            chunking_text.write("Đang chia nhỏ văn bản...")
            # Xử lý
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=int(chunk_size),
                chunk_overlap=int(chunk_overlap)
            )
            documents = text_splitter.split_documents(docs)
            # Ghi kết quả
            end_time = time.time()
            chunking_text.success(f"Đã chia nhỏ thành {len(documents)} chunk trong {round(end_time - start_time, 2)} giây")
            
            # ========== Embedding ==========
            start_time = time.time()
            embedding_text = st.empty()
            embedding_text.write("Đang tạo vector embedding...")
            # Xử lý
            embedder = HuggingFaceEmbeddings(
                model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
            vector_db = FAISS.from_documents(documents, embedder)
            st.session_state.retriever = vector_db.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 3}
            )
            # Ghi kết quả
            end_time = time.time()
            embedding_text.success(f"Đã tạo vector embedding trong {round(end_time - start_time, 2)} giây")
            
            status.update(label="PDF đã được xử lý thành công!", state="complete", expanded=False)
        st.success(":material/check_circle: Tài liệu đã sẵn sàng để hỏi đáp!")


# #####################
# UI lịch sử hội thoại
# #####################
st.header(":material/history: Lịch sử hội thoại")
for msg in st.session_state.chat_history_ui:
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.write(msg["content"])
            st.caption(f"Thời điểm: {msg['timestamp']}")
    else:
        with st.chat_message("assistant"):
            st.write(msg["content"])
            st.caption(f"Thời điểm: {msg['timestamp']} | Thời gian phản hồi: {msg['response_time']} giây")

# 5.3.2 Question Answering
st.header(":material/quiz: Đặt câu hỏi")
with st.form(key="question_form"):
    question = st.text_area(
        "Nhập câu hỏi của bạn tại đây:",
        placeholder="Tìm kiếm thông tin trong tài liệu...",
        height=140,
    )
    submit_question = st.form_submit_button(":material/send: Gửi câu hỏi")

# Nút bấm Primary Color (#007BFF)
if submit_question:
    if not uploaded_file:
        st.warning(":material/warning: Vui lòng tải lên tài liệu trước.")
    elif not question.strip():
        st.warning(":material/edit: Vui lòng nhập nội dung câu hỏi.")
    else:
        with st.spinner("AI đang trích xuất câu trả lời..."):
            # Lấy các đoạn văn bản liên quan (Context)
            if "retriever" not in st.session_state or st.session_state.retriever is None:
                st.warning("Chưa có dữ liệu để tìm kiếm.")
            else:
                #  Lưu trò chuyện của người dùng
                st.session_state.chat_history_ui.append({
                    "role": "user",
                    "content": question,
                    "timestamp": datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                    "response_time": None  # user thì không cần response_time
                })

                start_time = time.time()
                # Cấu hình mô hình LLM với các tham số tối ưu
                llm = OllamaLLM(
                    model="qwen2.5:7b",
                    temperature=0.7,      # Độ sáng tạo của câu trả lời
                    top_p=0.9,            # Kỹ thuật lấy mẫu nucleus sampling
                    repeat_penalty=1.1,   # Tránh lặp lại từ ngữ
                )
                relevant_docs = st.session_state.retriever.invoke(question)
                context = "\n".join([doc.page_content for doc in relevant_docs])
                
                # Lấy lịch sử hội thoại từ session state
                chat_history = st.session_state.chat_history_ui[-6:]
                history_text = "\n".join([
                    f"User: {m['content']}" if m["role"] == "user" else f"AI: {m['content']}"
                    for m in chat_history
                ])
                
                # Logic phát hiện tiếng Việt đơn giản
                vietnamese_chars = 'aaaaeeeiooouuuuyyyyd'
                is_vietnamese = any(char in question.lower() for char in vietnamese_chars)

                if is_vietnamese:
                    # Prompt tiếng Việt
                    prompt_template = f"""
Bạn là một AI trợ lý thông minh, chuyên trả lời câu hỏi dựa trên tài liệu.

Nhiệm vụ:
- Chỉ sử dụng thông tin từ "Ngữ cảnh" để trả lời
- Kết hợp với "Lịch sử hội thoại" để hiểu câu hỏi (đặc biệt là câu hỏi tiếp theo)
- Nếu không tìm thấy câu trả lời trong ngữ cảnh, hãy nói: "Tôi không biết"

Lịch sử hội thoại:
{history_text}

Ngữ cảnh:
{context}

Câu hỏi:
{question}

Trả lời:
- Rõ ràng
- Không bịa thông tin
- Trả lời bằng tiếng Việt
                    """                
                else:
                    # Prompt tiếng Anh
                    prompt_template = f"""
You are an intelligent AI assistant that answers questions based on provided documents.

Instructions:
- Use ONLY the information from the "Context"
- Use "Chat History" to understand follow-up questions
- If the answer is not in the context, say: "I don't know"

Chat History:
{history_text}

Context:
{context}

Question:
{question}

Answer:
- Be concise
- Do not hallucinate
                    """
                
                response = llm.invoke(prompt_template)
                end_time = time.time()
                elapsed_time = round(end_time - start_time, 2)
                # Lưu lịch sử phản hồi của robot
                st.session_state.chat_history_ui.append({
                    "role": "ai",
                    "content": response,
                    "timestamp": datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                    "response_time": elapsed_time
                })
                # Sinh câu trả lời
                st.markdown(f"**Thời gian phản hồi:** {elapsed_time} giây")
                st.markdown(f"**Câu hỏi:** {question}")
                st.markdown(f"**Trả lời:**\n{response}")