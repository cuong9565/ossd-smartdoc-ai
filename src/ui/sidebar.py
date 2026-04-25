import streamlit as st

def render_sidebar():
    with st.sidebar:
        # ========== HEADER ==========
        st.markdown("""
            <h1>🚀 SmartDoc AI</h1>
        """, unsafe_allow_html=True)

        # ========== QUICK GUIDE ==========
        st.subheader("🎯 Quick Guide", divider=False)
        st.markdown("""
        <div class="card">
            1️⃣ Settings<br/>
            2️⃣ Upload PDF<br/>
            3️⃣ Ask question<br/>
            4️⃣ Get answer
        </div>
        """, unsafe_allow_html=True)
        
        # ========== SYSTEM INFO ==========
        st.subheader("⚙️ System Info", divider=False)
        st.markdown(f"""
        <div class="card">
            📄 Format: <strong>PDF, WORD</strong><br/>
            📦 Max Size: <strong>50MB</strong><br/>
            🌐 Language: <strong>Tiếng Việt, English</strong><br/>
        </div>
        """, unsafe_allow_html=True)
        
        # ========== MODEL CONFIG ==========
        st.subheader("🤖 Models", divider=False)
        st.markdown("""
        <div class="card">
            🧠 <strong>LLM:</strong> qwen2.5:7b<br/>
            🔎 <strong>Embedding:</strong> MPNet<br/>
            🗄️ <strong>Vector DB:</strong> FAISS
        </div>
        """, unsafe_allow_html=True)
        
        # ========== ACTIONS CLEAR DATA ==========
        if st.session_state.retriever is not None:
            st.subheader("📋 Manage", divider=False)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Clear Chat", use_container_width=True):
                    st.session_state.chat_history_ui = []
                    st.toast("✓ Chat cleared")
                    st.rerun()
            with col2:
                if st.button("🗑️ Clear All", use_container_width=True):
                    st.session_state.retriever = None
                    st.session_state.vector_db = None
                    st.session_state.document_chunks = 0
                    st.session_state.uploaded_file_name = None
                    st.session_state.chat_history_ui = []
                    st.session_state.graph_triples = []
                    st.session_state.last_dual_responses = None
                    st.session_state.rag_mode = "RAG"
                    st.toast("✓ Reset done")
                    st.rerun()

        # ========== ACTIONS SELECT MODE ==========
        options_mode = ["RAG", "Graph RAG", "RAG, Graph RAG"]
        st.subheader("⚡ Mode", divider=False)
        rag_mode = st.selectbox(
            label = "Chọn chế độ RAG",
            options = options_mode,
            index = options_mode.index(st.session_state.rag_mode) if st.session_state.rag_mode in options_mode else 0
        )
        
        # ========== FOOTER ==========
        st.markdown("""
        <div style="
            text-align:center;
            margin-top:1.2rem;
            padding-top:0.8rem;
            font-size:0.7rem;
            opacity:0.5;
        ">
            © 2026 SmartDoc AI<br/>
            OSSD • Saigon University
        </div>
        """, unsafe_allow_html=True)

        return rag_mode
