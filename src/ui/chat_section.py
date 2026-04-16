import streamlit as st
import re                                     # regular expressions (Biểu thức chính quy)
from ..core import handle_answer_question

def render_chat_section():
    if st.session_state.retriever is not None:
        # UI Lịch sử trò chuyện
        render_chat_history()        
        
        # UI Đặt câu hỏi
        question, submit_question = render_chat_input()
        
        # Xử lý câu trả lời
        render_answer_question(question, submit_question)
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
    st.subheader("💬 Lịch sử hội thoại", divider=True)
    
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
    st.subheader("❓ Đặt câu hỏi", divider=True)
    
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

# UI xử lý câu trả lời
def render_answer_question(question, submit_question):
    if submit_question:
        if not question.strip():
            st.error("⚠️ Vui lòng nhập câu hỏi!")
            return
        
        with st.spinner("🔍 Đang xử lý..."):
            try:
                # Xử lý câu trả lời
                handle_answer_question(question)

                # Chạy lại UI để hiển thị câu trả lời
                st.rerun()
                
            except Exception as e:
                st.error(f"""
                ❌ **Lỗi xử lý**
                ```
                {str(e)}
                ```
                """)


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
    with st.expander(f"📄 Nguồn trích dẫn ({len(sources)} đoạn văn)", expanded=False):
        # Duyệt qua từng trích dẫn
        for i, src in enumerate(sources, 1):
            page_num   = src.get('page', 0) + 1            # Số trang
            chunk_idx  = src.get('chunk_index', '—')       # Chunk thứ mấy trong trang
            content    = src.get('content', '')            # Văn bản
            char_count = len(content)                      # Số lượng từ trong văn bản
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
