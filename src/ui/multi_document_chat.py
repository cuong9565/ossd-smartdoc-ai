import streamlit as st
import pandas as pd
import datetime

from ..advanced.qa_multi_document import answer_question
from ..advanced.benchmark_retrievers import benchmark_retriever
from ..core.filtering import filter_documents
from src.presistance.history_manager import save_messages

def render_multi_document_chat():
  st.divider()
  st.subheader("Chat với tài liệu")

  # ===== 1) LUÔN HIỂN THỊ LỊCH SỬ (theo sid) =====
  history = st.session_state.get("chat_history_ui") or []
  with st.expander(f"💬 Lịch sử hội thoại ({len(history)} messages)", expanded=True):
    if not history:
      st.info("Chưa có cuộc hội thoại cho sid này.")
    else:
      for msg in history:
        role = msg.get("role", "ai")
        ts = msg.get("timestamp") or ""
        if role == "user":
          with st.chat_message("user"):
            st.markdown(msg.get("content", ""))
            if ts:
              st.caption(f"⏰ {ts}")
        else:
          with st.chat_message("assistant"):
            st.markdown(msg.get("content", ""))
            rt = msg.get("response_time")
            if ts and rt is not None:
              st.caption(f"⏰ {ts} • ⚡ {rt}s")
            elif ts:
              st.caption(f"⏰ {ts}")

  # Nếu chưa upload docs thì chỉ hiển thị history, không cho hỏi tiếp
  has_docs = bool(st.session_state.get("documents"))
  if not has_docs:
    st.info("Bạn đã có lịch sử theo sid, nhưng để hỏi tiếp bạn cần upload và xử lý tài liệu.")
    return
  
  question = st.text_area("Nhập câu hỏi:", placeholder="Ví dụ: Tài liệu này nói về gì?", height=100, label_visibility="collapsed")

  # Chọn mode search
  mode = st.radio(
    "Chọn phương pháp search",
    ["Vector", "Hybrid"],
    horizontal=True,
  )

  # Option benchmark: chạy cả 2 luồng để so sánh
  run_benchmark = st.checkbox("Chạy benchmark (so sánh Vector vs Hybrid)", value=False)
  
  st.markdown("Lọc metadata")
  
  col1, col2, col3 = st.columns(3)
  
  unique_sources = sorted(
    set(doc.metadata.get("source") for doc in st.session_state.documents if doc.metadata.get("source"))
  )
  
  unique_file_types = sorted(
    set(doc.metadata.get("file_type") for doc in st.session_state.documents if doc.metadata.get("file_type"))
  )
  
  unique_upload_dates = sorted(
    set(doc.metadata.get("upload_date") for doc in st.session_state.documents if doc.metadata.get("upload_date"))
  )
  with col1:
        selected_source = st.selectbox(
            "Lọc theo file",
            ["Tất cả"] + unique_sources if unique_sources else ["Tất cả"],
        )
  with col2:
        selected_file_type = st.selectbox(
            "Lọc theo loại file",
            ["Tất cả"] + unique_file_types if unique_file_types else ["Tất cả"],
        )
  with col3:
        selected_upload_date = st.selectbox(
            "Lọc theo ngày upload",
            ["Tất cả"] + unique_upload_dates if unique_upload_dates else ["Tất cả"],
        )
  filters = {}
  if selected_source != "Tất cả":
    filters["source"] = selected_source
  if selected_file_type != "Tất cả":
    filters["file_type"] = selected_file_type
  if selected_upload_date != "Tất cả":
    filters["upload_date"] = selected_upload_date
  
  if st.button("Trả lời câu hỏi" , type="primary"):
    if not question.strip():
      st.error("Vui lòng nhập câu hỏi")
      return
    with st.spinner("Đang xử lý..."):
      try:
        # Lưu message user vào session + DB trước
        user_msg = {
          "role": "user",
          "content": question.strip(),
          "response": "",
          "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
          "response_time": None,
          "sources": [],
          "keywords": [],
          "mode": "multi-doc",
        }
        st.session_state.chat_history_ui.append(user_msg)
        try:
          save_messages(st.session_state.session_id, user_msg)
        except Exception:
          pass

        # Lọc documents theo metadata trước
        filtered_docs = filter_documents(
          st.session_state.documents,
          src=filters.get("source"),
          file_type=filters.get("file_type"),
          upload_date=filters.get("upload_date"),
        )

        if not filtered_docs:
          st.error("Không có document nào khớp filter.")
          return

        # Nếu bật benchmark thì chạy so sánh 2 luồng
        if run_benchmark:
          results = benchmark_retriever(
            questions=[question.strip()],
            documents=filtered_docs,
            retrieval_k=int(st.session_state.retrieval_k),
          )
          st.session_state.latest_benchmark_result = results[0] if results else None
          st.session_state.lastest_answer_result = None

          # Lưu một message assistant tóm tắt benchmark vào DB để reload vẫn thấy
          bench = st.session_state.latest_benchmark_result
          if bench:
            ai_msg = {
              "role": "ai",
              "content": f"[Benchmark]\n\nVector:\n{bench.get('pure_answer','')}\n\nHybrid:\n{bench.get('hybrid_answer','')}",
              "response": "",
              "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
              "response_time": bench.get("hybrid_total_time"),
              "sources": [],
              "keywords": [],
              "mode": "benchmark",
            }
            st.session_state.chat_history_ui.append(ai_msg)
            try:
              save_messages(st.session_state.session_id, ai_msg)
            except Exception:
              pass
        else:
          # Chạy theo mode được chọn
          selected_mode = "vector" if mode == "Vector" else "hybrid"
          result = answer_question(
            question=question.strip(),
            documents=filtered_docs,
            k=int(st.session_state.retrieval_k),
            filters=None,  # vì đã filter xong ở trên
            mode=selected_mode,
          )
          st.session_state.lastest_answer_result = result
          st.session_state.latest_benchmark_result = None

          # Lưu assistant answer vào session + DB
          ai_msg = {
            "role": "ai",
            "content": result.get("answer", ""),
            "response": result.get("answer", ""),
            "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
            "response_time": None,
            # Lưu sources/keywords nếu bạn muốn show lại trong history sau này
            "sources": [
              {
                "page": d.metadata.get("page", 0),
                "chunk_index": d.metadata.get("chunk_index", "—"),
                "content": d.page_content,
                "source": d.metadata.get("source"),
              }
              for d in (result.get("docs") or [])
            ],
            "keywords": [],
            "mode": selected_mode,
          }
          st.session_state.chat_history_ui.append(ai_msg)
          try:
            save_messages(st.session_state.session_id, ai_msg)
          except Exception:
            pass
      except Exception as e:
        st.error(f"Lỗi khi xử lý câu hỏi: {e}")
        return

  # Hiển thị kết quả answer (single mode)
  result = st.session_state.get("lastest_answer_result")
  if result:
    st.markdown("### Câu trả lời")
    st.write(result["answer"])

    st.markdown("### Nguồn trích dẫn")
    for doc in result["docs"]:
      source = doc.metadata.get("source", "unknown")
      page = doc.metadata.get("page", 0) + 1
      chunk_index = doc.metadata.get("chunk_index" , 0)
      st.write(f"- File: `{source}` | Page: {page} | Chunk: {chunk_index}")

  # Hiển thị benchmark (2 luồng)
  bench = st.session_state.get("latest_benchmark_result")
  if bench:
    st.markdown("### Benchmark: Vector vs Hybrid")

    col1, col2 = st.columns(2)
    with col1:
      st.markdown("#### Vector Search")
      st.write(bench["pure_answer"])
      st.caption(f"Top pages: {bench['pure_top_pages']}")
    with col2:
      st.markdown("#### Hybrid Search")
      st.write(bench["hybrid_answer"])
      st.caption(f"Top pages: {bench['hybrid_top_pages']}")

    # Bảng + biểu đồ performance
    df = pd.DataFrame([bench])
    st.markdown("### Bảng kết quả")
    st.dataframe(df, use_container_width=True)

    metrics_df = pd.DataFrame(
      {
        "Pipeline": ["Vector", "Hybrid"],
        "Retrieval Time (s)": [bench["pure_retrieval_time"], bench["hybrid_retrieval_time"]],
        "Generation Time (s)": [bench["pure_generation_time"], bench["hybrid_generation_time"]],
        "Total Time (s)": [bench["pure_total_time"], bench["hybrid_total_time"]],
      }
    ).set_index("Pipeline")

    st.markdown("### Biểu đồ so sánh")
    st.bar_chart(metrics_df, use_container_width=True)

    m1, m2, m3 = st.columns(3)
    with m1:
      st.metric("Vector Total", f"{bench['pure_total_time']:.4f}s")
    with m2:
      st.metric("Hybrid Total", f"{bench['hybrid_total_time']:.4f}s")
    with m3:
      st.metric("Hybrid - Vector", f"{(bench['hybrid_total_time'] - bench['pure_total_time']):.4f}s")