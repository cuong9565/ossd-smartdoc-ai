import streamlit as st

def render_sidebar():
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
