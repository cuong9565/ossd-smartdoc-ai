import streamlit as st
import re                                     # regular expressions (Biểu thức chính quy)
import pandas as pd

from ..core import handle_answer_question, handle_answer_question_multi
from ..core.handle_answer_question import handle_benchmark_question

def render_chat_section():
    if st.session_state.rag_mode["name"] is not None:
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
            <p style="color: #0C5460; margin: 0; font-size: 0.95rem;">Sử dụng mục "Tải file pdf hoặc word" phía trên</p>
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
            ts = msg.get("timestamp") or ""
            # UI cho user
            if msg["role"] == "user":
                with st.chat_message("user", avatar="👤"):
                    st.markdown(msg["content"])
                    if ts:
                        st.caption(f"⏰ {ts}", unsafe_allow_html=False)
            # UI cho AI
            else:
                # Benchmark message (persisted inside sources)
                bench_row = None
                for s in (msg.get("sources") or []):
                    if isinstance(s, dict) and "benchmark" in s:
                        bench_row = s.get("benchmark")
                        break

                if bench_row:
                    with st.chat_message("assistant", avatar="🤖"):
                        st.markdown("### Benchmark: Vector vs Hybrid")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("#### Vector Search")
                            st.write(bench_row.get("pure_answer", ""))
                            st.caption(f"Total: {bench_row.get('pure_total_time')}s")
                        with col2:
                            st.markdown("#### Hybrid Search")
                            st.write(bench_row.get("hybrid_answer", ""))
                            st.caption(f"Total: {bench_row.get('hybrid_total_time')}s")

                        metrics_df = pd.DataFrame(
                            {
                                "Pipeline": ["Vector", "Hybrid"],
                                "Retrieval Time (s)": [bench_row.get("pure_retrieval_time", 0), bench_row.get("hybrid_retrieval_time", 0)],
                                "Generation Time (s)": [bench_row.get("pure_generation_time", 0), bench_row.get("hybrid_generation_time", 0)],
                                "Total Time (s)": [bench_row.get("pure_total_time", 0), bench_row.get("hybrid_total_time", 0)],
                            }
                        ).set_index("Pipeline")
                        st.bar_chart(metrics_df, use_container_width=True)
                        st.caption(f"⏰ {ts}", unsafe_allow_html=False)
                    continue

                # Dual message: chỉ render 2 cột khi message thực sự là dual (không phụ thuộc rag_mode hiện tại)
                is_dual = bool(msg.get("dual")) or ("rag" in msg and "graph" in msg)
                if is_dual:
                    # Hiển thị dual responses với 2 cột
                    left_col, right_col = st.columns(2)
                    with left_col:
                        st.markdown("### RAG")
                        rag_msg = msg.get("rag", {})
                        st.write(rag_msg.get("content", ""))
                        st.caption(f"⏰ {ts} • ⚡ {rag_msg.get('response_time', 0)}s")
                        # Sources cho RAG
                        _hist_sources_rag = rag_msg.get('sources', [])
                        _hist_keywords_rag = rag_msg.get('keywords', [])
                        if _hist_sources_rag:
                            render_sources_ui(_hist_sources_rag, _hist_keywords_rag)
                    with right_col:
                        st.markdown("### Graph RAG")
                        graph_msg = msg.get("graph", {})
                        st.write(graph_msg.get("content", ""))
                        st.caption(f"⏰ {ts} • ⚡ {graph_msg.get('response_time', 0)}s")
                else:
                    with st.chat_message("assistant", avatar="🤖"):
                        st.markdown(msg.get("content", ""))
                        response_time = msg.get('response_time', 0)
                        st.caption(f"⏰ {ts} • ⚡ {response_time}s")
                        # ── Citation tracking: hiển thị lại sources trong history (chỉ cho RAG, không cho Graph RAG) ──
                        _hist_sources   = msg.get('sources', [])
                        _hist_keywords  = msg.get('keywords', [])
                        if msg.get('mode') != "Graph RAG" and _hist_sources:
                            render_sources_ui(_hist_sources, _hist_keywords)

def render_chat_input():
    if st.session_state.rag_mode["name"] is not None:
        st.divider()
        st.subheader("❓ Đặt câu hỏi", divider=True)
        
        # Option retrieval mode for RAG: Vector vs Hybrid
        if "search_mode" not in st.session_state:
            st.session_state.search_mode = "Vector"
        st.radio(
            "Chọn chế độ search",
            ["Vector", "Hybrid"],
            key="search_mode",
            horizontal=True,
        )

        # Fairness toggle: apply Cross-Encoder rerank for both Vector/Hybrid
        if "use_rerank" not in st.session_state:
            st.session_state.use_rerank = False
        st.checkbox(
            "Bật Re-ranking (Cross-Encoder) để so sánh công bằng",
            key="use_rerank",
            value=st.session_state.use_rerank,
        )

        # Benchmark option (Vector vs Hybrid)
        if "run_benchmark" not in st.session_state:
            st.session_state.run_benchmark = False
        st.checkbox(
            "Chạy benchmark (so sánh Vector vs Hybrid)",
            key="run_benchmark",
            value=st.session_state.run_benchmark,
        )

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
                if st.session_state.rag_mode["name"] == "RAG, Graph RAG":
                    handle_answer_question_multi(question)
                else:
                    # Benchmark overrides single answer
                    if st.session_state.get("run_benchmark"):
                        handle_benchmark_question(question)
                    else:
                        # Pass retrieval mode for RAG path (Vector/Hybrid)
                        handle_answer_question(question, mode=st.session_state.rag_mode["name"])

                st.rerun()

            except Exception as e:
                st.error(f"❌ **Lỗi xử lý: **{str(e)}")

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
            file_name  = src.get('source', 'Unknown')      # Tên file
            content    = src.get('content', '')            # Văn bản
            char_count = len(content)                      # Số lượng từ trong văn bản
            body       = highlight_text(content, keywords) 
            st.markdown(f"""
            <div class="source-card-enhanced">
                <div class="source-header">
                    <div style="display: flex; flex-direction: column;">
                        <span class="source-title">📌 Nguồn {i}</span>
                    </div>
                    <div class="source-badges">
                        <span class="file-badge">📁 File&nbsp;{file_name}</span>
                        <span class="page-badge">📄 Trang&nbsp;{page_num}</span>
                        <span class="chunk-badge">🧩 Chunk&nbsp;{chunk_idx}</span>
                        <span class="len-badge">📏 {char_count}&nbsp;ký&nbsp;tự</span>
                    </div>
                </div>
                <div class="source-content">{body}</div>
            </div>
            """, unsafe_allow_html=True)
