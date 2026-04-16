import streamlit as st
import os

def get_vietnamese_template(history_text, context, question):
    return f"""Bạn là một AI trợ lý thông minh, chuyên trả lời câu hỏi dựa trên tài liệu.
        Nhiệm vụ:
        - Chỉ sử dụng thông tin từ "Ngữ cảnh" để trả lời
        - Kết hợp với "Lịch sử hội thoại" để hiểu câu hỏi (đặc biệt là câu hỏi tiếp theo)
        - Nếu không tìm thấy câu trả lời trong ngữ cảnh, hãy nói: "Tôi không biết"

        LỊCH SỬ HỘI THOẠI:
        {history_text}

        NGỮ CẢNH:
        {context}

        CÂU HỎI:
        {question}

        TRẢ LỜI (tiếng Việt):
    """

def get_english_template(history_text, context, question):
    return f"""You are an intelligent AI assistant that answers questions based on provided documents.
        Instructions:
        - Use ONLY the information from the "Context"
        - Use "Chat History" to understand follow-up questions
        - If the answer is not in the context, say: "I don't know"

        CHAT HISTORY:
        {history_text}

        CONTEXT:
        {context}

        QUESTION:
        {question}

        ANSWER (english):
    """

# @Function: Phát hiện ngôn ngữ
# @Param text (string): chuỗi cần detect
# @Return: chuỗi đó có phải tiếng việt không
# #
def detect_is_vietnamese(text):
    vietnamese_chars = set(
        "áàảãạăắằẳẵặâấầẩẫậ"
        "éèẻẽẹêếềểễệ"
        "íìỉĩị"
        "óòỏõọôốồổỗộơớờởỡợ"
        "úùủũụưứừửữự"
        "ýỳỷỹỵ"
        "đ"
    )

    return any(char in text.lower() for char in vietnamese_chars)