import streamlit as st
import os

def get_vietnamese_template(history_text, context, question):
    return f"""Bạn là trợ lý AI trả lời câu hỏi dựa trên tài liệu được cung cấp.
        Bạn hãy
        - Trả lời "CÂU HỎI" dựa trên thông tin từ phần "NGỮ CẢNH"
        - Nếu không có câu trả lời trong ngữ cảnh, trả lời: "Tôi không có thông tin về điều này."

        LỊCH SỬ HỘI THOẠI:
        {history_text}

        NGỮ CẢNH:
        {context}

        CÂU HỎI:
        {question}

        TRẢ LỜI (tiếng Việt):
    """

def get_english_template(history_text, context, question):
    return f"""You are an AI assistant that answers questions based strictly on provided documents.
        Please
        - Answer the "QUESTION" based on information from the "CONTEXT" section.
        - If there is no answer in the context, reply: "I don't have information about this."

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