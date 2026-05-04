import streamlit as st
import os
def get_file_context_template():
    return """
    Nhiệm vụ:
    - Phân tích văn bản được trích từ phần đầu của tài liệu.
    - Ưu tiên trích xuất thông tin từ phần **Mục lục (Table of Contents / Contents)** nếu có.
    - Bỏ qua các phần không liên quan như: lời cảm ơn, lời nói đầu, lời giới thiệu, preface, acknowledgment.
    - Nếu không tìm thấy mục lục, suy luận từ các tiêu đề (heading) hoặc nội dung chính.

    Yêu cầu:
    - Chỉ sử dụng thông tin mang tính cấu trúc (mục lục hoặc tiêu đề chính), không dùng các đoạn văn mang tính cảm xúc hoặc giới thiệu.
    - Tóm tắt ngắn gọn, đúng trọng tâm.

    Chỉ trả về đúng định dạng sau (không giải thích thêm):
    - Lĩnh vực: (Ví dụ: Khoa học máy tính, Y học, Kinh tế...)
    - Chủ đề chính: (Tên sách hoặc nội dung cốt lõi)
    - Từ khóa chuyên ngành: (3-5 từ khóa quan trọng nhất)

    Văn bản:
    {text}

    Hồ sơ tài liệu:
    """

def rewrite_vietnamese_template():
    return """Bạn là một chuyên gia tối ưu hóa tìm kiếm thông tin.
    Tài liệu hiện tại hệ thống đang sử dụng có thông tin hồ sơ như sau:
    {profile}

    Nhiệm vụ:
    
    - Dựa vào hồ sơ tài liệu và ngữ cảnh trò chuyện, viết lại câu hỏi của người dùng để làm rõ mọi đại từ (nó, phương pháp này, thuật toán đó...) thành các danh từ/thuật ngữ cụ thể.
    - Nếu câu hỏi dùng từ lóng hoặc từ viết tắt, hãy dịch/làm rõ chúng sang thuật ngữ chuyên môn thuộc lĩnh vực của tài liệu (Ví dụ: "QHD" -> "Quy hoạch động").
    - Tuyệt đối không tự ý suy diễn sang các lĩnh vực không liên quan đến hồ sơ tài liệu đã cho.
    - KHÔNG trả lời câu hỏi.
    - CHỈ in ra duy nhất câu hỏi đã được viết lại, không giải thích gì thêm.

    Lịch sử trò chuyện gần đây:
    {history}

    Câu hỏi ban đầu: {question}
    Câu hỏi tối ưu:"""
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