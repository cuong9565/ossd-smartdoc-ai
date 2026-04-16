import streamlit as st
import tempfile
import os
from ..core import load_pdf, chunk_pdf, embedding

def document_processing(uploaded_file, chunk_size, chunk_overlap, retrieval_k):
    if uploaded_file and st.session_state.retriever is None:
        file_size_mb = uploaded_file.size / (1024 * 1024)
        
        # If size file > 50MB
        if file_size_mb > 50:
            st.error(f"❌ File quá lớn ({file_size_mb:.2f}MB > 50MB)")
            return
        
        # Save temporary file to memory
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.getbuffer())
            temp_path = tmp.name
        
        # Save name file in session
        st.session_state.uploaded_file_name = uploaded_file.name
        
        # Processing with status
        with st.status("🔄 Đang phân tích tài liệu...", expanded=True) as status:
            try:
                # Load PDF
                step1 = st.empty()
                step1.write("📖 Bước 1/3: Trích xuất văn bản từ PDF...")
                elapsed, docs = load_pdf(temp_path)
                step1.success(f"✓ Trích xuất xong: {len(docs)} trang trong {elapsed}s")
                
                # Chunking pdf
                step2 = st.empty()
                step2.write("✂️ Bước 2/3: Chia nhỏ văn bản thành chunks...")
                elapsed, documents = chunk_pdf(chunk_size, chunk_overlap, docs)
                step2.success(f"✓ Chunking xong: {len(documents)} chunks trong {elapsed}s")
                
                # Embedding
                step3 = st.empty()
                step3.write("🔢 Bước 3/3: Tạo vector embeddings...")
                elapsed = embedding(documents, retrieval_k)
                step3.success(f"✓ Embedding xong trong {elapsed}s")

                # Update ui success
                status.update(
                    label="PDF đã xử lý thành công!",
                    state="complete",
                    expanded=False
                )
                st.success("""
                :material/check_circle: **Tài liệu sẵn sàng!**  
                Bạn có thể bắt đầu đặt câu hỏi được rồi.
                """)
                
            except Exception as e:
                status.update(
                    label="❌ Xử lý thất bại",
                    state="error",
                    expanded=True
                )
                st.error(
                    f"""
                    **Có lỗi xảy ra khi xử lý tài liệu**
                    **Chi tiết lỗi:**
                    {str(e)}
                    """,
                    icon="🚨"
                )
            
            finally:
                # Clean up temp file
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass
