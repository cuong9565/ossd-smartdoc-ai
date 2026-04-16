import streamlit as st

def render_page():
    st.set_page_config(
        page_title="SmartDoc AI",
        page_icon=":material/description:",
        layout="wide",
        initial_sidebar_state="expanded"
    )