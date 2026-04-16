import streamlit as st

def render_header():
    st.markdown("""
    <div style="text-align: center; margin-bottom: 1.5rem;">
        <h1 style="margin: 0; color: #212529; font-size: 2.2rem;">🚀 SmartDoc AI</h1>
        <p style="margin: 0.3rem 0 0 0; color: #6C757D; font-size: 1rem;">Intelligent Document Q&A System</p>
    </div>
    """, unsafe_allow_html=True)