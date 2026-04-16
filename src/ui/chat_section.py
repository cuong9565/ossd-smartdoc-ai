import streamlit as st
from langchain_ollama import OllamaLLM                               # gọi LLM chạy local
import time
import datetime
import re                                     # regular expressions (Biểu thức chính quy)

def render_chat_section():
    if st.session_state.retriever is not None:
        # UI Lịch sử trò chuyện
        render_chat_history()        
        
        # UI Đặt câu hỏi
        question, submit_question = render_chat_input()
        
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
                            prompt_template = f"""Bạn là trợ lý AI trả lời câu hỏi dựa trên tài liệu được cung cấp.
                                Bạn hãy
                                - Trả lời "CÂU HỎI" dựa trên thông tin từ phần "NGỮ CẢNH"
                                - Nếu không có câu trả lời trong ngữ cảnh, trả lời: "Tôi không có thông tin về điều này"

                                LỊCH SỬ HỘI THOẠI:
                                {history_text}

                                NGỮ CẢNH:
                                {context}

                                CÂU HỎI:
                                {question}

                                TRẢ LỜI (tiếng Việt):
                            """
                        else:
                            prompt_template = f"""You are an AI assistant that answers questions based strictly on provided documents.
                                Please
                                - Answer the "QUESTION" based on information from the "CONTEXT" section.
                                - If there is no answer in the context, reply: "I don't have information about this."

                                CHAT HISTORY:
                                {history_text}

                                CONTEXT:
                                {context}

                                QUESTION:
                                {question}

                                ANSWER (english):
                            """
                        
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

def render_chat_history():
    st.divider()
    st.subheader("💬 Lịch sử hội thoại (Bước 3)", divider=True)
    
    # Nếu không có lịch sử hội thoại
    if len(st.session_state.chat_history_ui) == 0:
        st.markdown("""
        <div style="text-align: center; padding: 1.5rem; color: #6C757D;">
            <p style="font-size: 1rem; margin: 0; opacity: 0.7;">Chưa có cuộc hội thoại</p>
        </div>
        """, unsafe_allow_html=True)
    # Nếu có lịch sử hội thoại
    else:
        for i, msg in enumerate(st.session_state.chat_history_ui):
            # UI cho user
            if msg["role"] == "user":
                with st.chat_message("user", avatar="👤"):
                    st.markdown(msg["content"])
                    st.caption(f"⏰ {msg['timestamp']}", unsafe_allow_html=False)
            # UI cho AI
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

def render_chat_input():
    st.divider()
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
    
    return question, submit_question

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
