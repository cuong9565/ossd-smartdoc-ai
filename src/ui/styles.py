import streamlit as st

def load_css():
    st.markdown("""
        <style>
            /* ============== GLOBAL STYLES ============== */
            * {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }

            .stApp {
                background-color: #F8F9FA;
                color: #212529;
            }

            hr {
                border: none !important;
                border-top: 1px solid #E3E6EB !important;
                margin: 0.75rem 0 !important;
            }

            /* ============== SIDEBAR STYLING (#2C2F33) ============== */
            [data-testid="stSidebar"] {
                background-color: #2C2F33;
                background-image: linear-gradient(135deg, #2C2F33 0%, #1a1d20 100%);
            }

            [data-testid="stSidebarUserContent"] {
                padding-top: 1rem !important;
                padding-bottom: 2rem !important;
                padding-left: 1.25rem !important;
                padding-right: 1.25rem !important;
            }

            [data-testid="stSidebar"] h1, 
            [data-testid="stSidebar"] h2, 
            [data-testid="stSidebar"] h3,
            [data-testid="stSidebar"] .stMarkdown,
            [data-testid="stSidebar"] p {
                color: #FFFFFF !important;
            }

            [data-testid="stSidebar"] .stInfo {
                background-color: rgba(0, 123, 255, 0.1) !important;
                border-left: 4px solid #007BFF !important;
                border-radius: 0.5rem;
                padding: 0.75rem !important;
            }

            [data-testid="stSidebar"] .stInfo p {
                color: #FFFFFF !important;
                margin: 0 !important;
            }

            /* ============== BUTTON STYLING ============== */
            .stButton > button {
                background-color: #007BFF;
                color: white;
                border-radius: 8px;
                border: none;
                font-weight: 600;
                padding: 0.6rem 1.2rem;
                transition: all 0.3s ease;
                box-shadow: 0 2px 4px rgba(0, 123, 255, 0.2);
            }

            .stButton > button:hover {
                background-color: #0056b3;
                box-shadow: 0 4px 12px rgba(0, 123, 255, 0.4);
                transform: translateY(-2px);
            }

            .stButton > button:active {
                transform: translateY(0);
            }

            /* Danger buttons */
            .danger-btn {
                background-color: #DC3545 !important;
            }

            .danger-btn:hover {
                background-color: #C82333 !important;
                box-shadow: 0 4px 12px rgba(220, 53, 69, 0.4) !important;
            }

            /* ============== FILE UPLOADER ============== */
            [data-testid="stFileUploader"] {
                border: 2px dashed #FFC107 !important;
                padding: 2rem !important;
                border-radius: 12px !important;
                background-color: #FFFBF0 !important;
                transition: all 0.3s ease;
            }

            [data-testid="stFileUploader"]:hover {
                border-color: #FF9800 !important;
                background-color: #FFF8E1 !important;
                box-shadow: 0 4px 12px rgba(255, 152, 0, 0.1);
            }

            /* ============== FORM & INPUT ELEMENTS ============== */
            .stTextArea textarea {
                min-height: 140px !important;
                border-radius: 10px !important;
                padding: 14px !important;
                border: 1.5px solid #E3E6EB !important;
                background-color: #FFFFFF !important;
                color: #212529 !important;
                font-size: 14px !important;
                transition: all 0.3s ease;
            }

            .stTextArea textarea:focus {
                border-color: #007BFF !important;
                box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1) !important;
            }

            .stNumberInput input {
                border-radius: 8px !important;
                border: 1.5px solid #E3E6EB !important;
            }

            .stNumberInput input:focus {
                border-color: #007BFF !important;
            }

            /* ============== CARDS & CONTAINERS ============== */
            .card {
                background-color: #FFFFFF;
                border-radius: 12px;
                padding: 20px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
                border: 1px solid #E3E6EB;
                margin: 0.5rem 0;
                transition: all 0.3s ease;
            }

            .card:hover {
                box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
                border-color: #DEE2E6;
            }

            .answer-card {
                background-color: #FFFFFF;
                padding: 20px;
                border-radius: 12px;
                border-left: 5px solid #007BFF;
                box-shadow: 0 2px 12px rgba(0, 123, 255, 0.08);
                color: #212529;
                margin: 0.5rem 0;
            }

            .source-card {
                background-color: #F0F7FF;
                padding: 15px;
                border-radius: 10px;
                border-left: 4px solid #28A745;
                margin: 0.3rem 0;
                color: #212529;
                font-size: 13px;
            }

            .info-box {
                background-color: #E7F3FF;
                border-left: 4px solid #007BFF;
                padding: 12px 16px;
                border-radius: 6px;
                margin: 0.75rem 0;
            }

            /* ============== STATUS & ALERT MESSAGES ============== */
            .stAlert {
                border-radius: 10px !important;
                border: none !important;
                padding: 1rem !important;
            }

            .stSuccess {
                background-color: #D4EDDA !important;
                color: #155724 !important;
            }

            .stError {
                background-color: #F8D7DA !important;
                color: #721C24 !important;
            }

            .stWarning {
                background-color: #FFF3CD !important;
                color: #856404 !important;
            }

            .stInfo {
                background-color: #D1ECF1 !important;
                color: #0C5460 !important;
            }

            /* ============== HEADERS & TEXT ============== */
            h1 {
                color: #212529 !important;
                margin-bottom: 0.5rem !important;
                font-weight: 700 !important;
                font-size: 2.5rem !important;
            }

            h2 {
                color: #212529 !important;
                margin-top: 0.75rem !important;
                margin-bottom: 0.5rem !important;
                font-weight: 700 !important;
                border-bottom: 2px solid #E3E6EB;
                padding-bottom: 0.5rem;
            }

            h3 {
                color: #212529 !important;
                margin-top: 0.5rem !important;
                margin-bottom: 0.5rem !important;
                font-weight: 600 !important;
            }

            /* ============== CHAT MESSAGES ============== */
            .stChatMessage {
                padding: 0.75rem !important;
                background-color: #FFFFFF !important;
                border-radius: 12px !important;
                margin: 0.4rem 0 !important;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04) !important;
            }

            /* ============== METRICS ============== */
            .metric-badge {
                display: inline-block;
                background-color: #007BFF;
                color: white;
                padding: 0.4rem 0.8rem;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 600;
                margin: 0.25rem 0.25rem 0.25rem 0;
            }

            /* ============== ANIMATIONS ============== */
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }

            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.7; }
            }

            .fade-in {
                animation: fadeIn 0.3s ease;
            }

            .pulse {
                animation: pulse 2s ease-in-out infinite;
            }

            /* ============== UTILITY CLASSES ============== */
            .divider-line {
                border: none;
                border-top: 1px solid #E3E6EB;
                margin: 1.5rem 0;
            }

            .text-muted {
                color: #6C757D;
                font-size: 0.9rem;
            }

            .text-success {
                color: #28A745;
                font-weight: 600;
            }

            .text-danger {
                color: #DC3545;
                font-weight: 600;
            }

            /* ============== CITATION / SOURCE TRACKING ============== */
            mark.kw-highlight {
                background-color: #FFF176;
                color: #212529;
                padding: 1px 4px;
                border-radius: 3px;
                font-weight: 600;
                box-shadow: 0 1px 2px rgba(255,241,118,0.5);
            }

            .source-card-enhanced {
                background-color: #F8FAFC;
                padding: 14px 16px;
                border-radius: 10px;
                border-left: 4px solid #28A745;
                margin: 0.55rem 0;
                color: #212529;
                transition: box-shadow 0.25s ease, border-left-color 0.25s ease;
                box-shadow: 0 1px 4px rgba(0,0,0,0.05);
            }

            .source-card-enhanced:hover {
                box-shadow: 0 4px 14px rgba(40,167,69,0.14);
                border-left-color: #1E7E34;
            }

            .source-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 10px;
                flex-wrap: wrap;
                gap: 6px;
            }

            .source-title {
                font-weight: 700;
                font-size: 0.95rem;
                color: #212529;
            }

            .source-badges {
                display: flex;
                gap: 6px;
                flex-wrap: wrap;
            }

            .page-badge {
                display: inline-flex;
                align-items: center;
                background: linear-gradient(135deg, #007BFF 0%, #0056b3 100%);
                color: white;
                padding: 3px 10px;
                border-radius: 12px;
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 0.3px;
            }

            .chunk-badge {
                display: inline-flex;
                align-items: center;
                background: linear-gradient(135deg, #28A745 0%, #1E7E34 100%);
                color: white;
                padding: 3px 10px;
                border-radius: 12px;
                font-size: 11px;
                font-weight: 600;
            }

            .len-badge {
                display: inline-flex;
                align-items: center;
                background: linear-gradient(135deg, #6C757D 0%, #495057 100%);
                color: white;
                padding: 3px 10px;
                border-radius: 12px;
                font-size: 11px;
                font-weight: 600;
            }

            .source-content {
                font-size: 0.875rem;
                line-height: 1.75;
                color: #343A40;
                padding: 10px 12px;
                background-color: #FFFFFF;
                border-radius: 6px;
                border: 1px solid #E9ECEF;
                max-height: 280px;
                overflow-y: auto;
                word-wrap: break-word;
                white-space: pre-wrap;
            }
        </style>
    """, unsafe_allow_html=True
    )
