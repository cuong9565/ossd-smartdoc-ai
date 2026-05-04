import pandas as pd
import streamlit as st

from ..advanced.benchmark_retrievers import benchmark_retriever


def _latest_user_question():
  for msg in reversed(st.session_state.chat_history_ui):
    if msg.get("role") == "user":
      return msg.get("content", "").strip()
  return ""


def render_benchmark_section():
  if not st.session_state.documents:
    return

  st.divider()
  st.subheader("So sánh Vector Search và Hybrid Search")
  st.caption("Nhập một câu hỏi bất kỳ để chạy đồng thời 2 luồng và so sánh kết quả.")

  question = st.text_area(
    "Câu hỏi benchmark",
    placeholder="Ví dụ: N-List là gì?",
    key="benchmark_question",
    height=90,
  )

  if st.button("Chạy benchmark", type="primary"):
    final_question = question.strip() or _latest_user_question()
    if not final_question:
      st.error("⚠️ Vui lòng nhập câu hỏi benchmark hoặc hỏi trong khung chat trước.")
      return

    with st.spinner("Đang chạy benchmark cho Vector Search và Hybrid Search..."):
      results = benchmark_retriever(
        questions=[final_question],
        documents = st.session_state.documents,
        retrieval_k = st.session_state.retrieval_k,
      )
      df = pd.DataFrame(results)

      df["retrieval_diff"] = df["hybrid_retrieval_time"] - df["pure_retrieval_time"]
      df["generation_diff"] = df["hybrid_generation_time"] - df["pure_generation_time"]
      df["total_diff"] = df["hybrid_total_time"] - df["pure_total_time"]

      benchmark_row = df.iloc[0]

      st.markdown("### Câu trả lời theo từng luồng")
      col1, col2 = st.columns(2)
      with col1:
        st.markdown("#### Vector Search")
        st.write(benchmark_row["pure_answer"])
        st.caption(f"Top pages: {benchmark_row['pure_top_pages']}")
      with col2:
        st.markdown("#### Hybrid Search")
        st.write(benchmark_row["hybrid_answer"])
        st.caption(f"Top pages: {benchmark_row['hybrid_top_pages']}")

      st.markdown("### Kết quả chi tiết")
      st.dataframe(df, use_container_width=True)

      st.markdown("### Biểu đồ so sánh hiệu năng")
      chart_col1, chart_col2, chart_col3 = st.columns(3)

      retrieval_df = pd.DataFrame(
        {
          "Pipeline": ["A Vector", "B Hybrid"],
          "Retrieval Time (s)": [benchmark_row["pure_retrieval_time"], benchmark_row["hybrid_retrieval_time"]],
        }
      ).set_index("Pipeline")

      generation_df = pd.DataFrame(
        {
          "Pipeline": ["A Vector", "B Hybrid"],
          "Generation Time (s)": [benchmark_row["pure_generation_time"], benchmark_row["hybrid_generation_time"]],
        }
      ).set_index("Pipeline")

      total_df = pd.DataFrame(
        {
          "Pipeline": ["A Vector", "B Hybrid"],
          "Total Time (s)": [benchmark_row["pure_total_time"], benchmark_row["hybrid_total_time"]],
        }
      ).set_index("Pipeline")

      with chart_col1:
        st.caption("Retrieval")
        st.bar_chart(retrieval_df, use_container_width=True)

      with chart_col2:
        st.caption("Generation")
        st.bar_chart(generation_df, use_container_width=True)

      with chart_col3:
        st.caption("Total")
        st.bar_chart(total_df, use_container_width=True)


      st.markdown("### Tóm tắt metrics")
      m1, m2, m3 = st.columns(3)
      with m1:
        st.metric("Vector Total", f"{benchmark_row['pure_total_time']:.4f}s")
      with m2:
        st.metric("Hybrid Total", f"{benchmark_row['hybrid_total_time']:.4f}s")
      with m3:
        st.metric("Hybrid - Vector", f"{benchmark_row['total_diff']:.4f}s")

      m4, m5, m6 = st.columns(3)
      with m4:
        st.metric("Vector Retrieval", f"{benchmark_row['pure_retrieval_time']:.4f}s")
      with m5:
        st.metric("Hybrid Retrieval", f"{benchmark_row['hybrid_retrieval_time']:.4f}s")
      with m6:
        st.metric("Context size (chars)", f"{benchmark_row['hybrid_context_length']} / {benchmark_row['pure_context_length']}")

      m7, m8 = st.columns(2)
      with m7:
        st.metric("Vector chunks", int(benchmark_row["pure_num_chunks"]))
      with m8:
        st.metric("Hybrid chunks", int(benchmark_row["hybrid_num_chunks"]))