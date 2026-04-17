import os
import tempfile

import streamlit as st

from ..core import chunk_pdf, embedding, load_pdf


def document_processing(uploaded_file, chunk_size, chunk_overlap, retrieval_k):
    if uploaded_file and st.session_state.retriever is None:
        file_size_mb = uploaded_file.size / (1024 * 1024)

        # Chặn file quá lớn để tránh tốn RAM khi xử lý PDF.
        if file_size_mb > 50:
            st.error(f"❌ File quá lớn ({file_size_mb:.2f}MB > 50MB)")
            return

        # Khởi tạo trước để tránh lỗi nếu exception xảy ra trước khi temp_path được gán.
        temp_path = None

        # Lưu file upload ra file tạm để loader đọc.
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.getbuffer())
            temp_path = tmp.name

        # Lưu tên file để UI hiển thị trạng thái tài liệu.
        st.session_state.uploaded_file_name = uploaded_file.name

        # Chạy từng bước xử lý trong một status block.
        with st.status("🔄 Đang phân tích tài liệu...", expanded=True) as status:
            try:
                # Bước 1: đọc PDF thành các trang document.
                step1 = st.empty()
                step1.write("📖 Bước 1/3: Trích xuất văn bản từ PDF...")
                elapsed, docs = load_pdf(temp_path)
                step1.success(f"✓ Trích xuất xong: {len(docs)} trang trong {elapsed}s")

                # Bước 2: chia trang thành các chunk nhỏ.
                step2 = st.empty()
                step2.write("✂️ Bước 2/3: Chia nhỏ văn bản thành chunks...")
                elapsed, documents = chunk_pdf(chunk_size, chunk_overlap, docs)
                step2.success(f"✓ Chunking xong: {len(documents)} chunks trong {elapsed}s")

                # Bước 3: tạo hybrid retriever để tìm theo nghĩa + từ khóa.
                step3 = st.empty()
                step3.write("🔢 Bước 3/3: Tạo hybrid retriever...")
                elapsed = embedding(documents, retrieval_k)
                step3.success(f"✓ Tạo retriever xong trong {elapsed}s")
                

                # Báo UI là tài liệu đã sẵn sàng.
                status.update(
                    label="PDF đã xử lý thành công!",
                    state="complete",
                    expanded=False,
                )
                st.success(
                    ":material/check_circle: **Tài liệu sẵn sàng!**  \n"
                    "Bạn có thể bắt đầu đặt câu hỏi được rồi."
                )

            except Exception as e:
                # Nếu có lỗi thì hiển thị ngay cho người dùng.
                status.update(
                    label="❌ Xử lý thất bại",
                    state="error",
                    expanded=True,
                )
                st.error(
                    f"""
                    **Có lỗi xảy ra khi xử lý tài liệu**
                    **Chi tiết lỗi:**
                    {str(e)}
                    """,
                    icon="🚨",
                )

            finally:
                # Xoá file tạm để tránh rác trên ổ đĩa.
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass
