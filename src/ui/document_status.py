import streamlit as st

def render_document_status_ui():
    if st.session_state.retriever is not None:
        with st.container():
            st.markdown("""
            <div style="background-color: #E7F3FF; border-left: 4px solid #007BFF; padding: 0.75rem; border-radius: 8px; margin: 0.5rem 0;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <p style="margin: 0; color: #0C5460; font-weight: 600; font-size: 0.95rem;">📄 Tài liệu: <strong>""" + 
                        str(st.session_state.document_chunks) + """ chunks</strong></p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)