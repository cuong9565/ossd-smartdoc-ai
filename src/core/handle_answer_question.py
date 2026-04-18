import streamlit as st
import time
import datetime
import re                                     # regular expressions (Biểu thức chính quy)

from langchain_core.prompts import PromptTemplate

from .config import Config
from .prompt_template import rewrite_vietnamese_template,detect_is_vietnamese, get_vietnamese_template, get_english_template

def call_llm_to_rewrite(history_text,question):

    rewrite_template=rewrite_vietnamese_template(history_text,question)
    prompt= PromptTemplate(
        template=rewrite_template,
        input_variables=["question"],
    )

    rewrite_chain=prompt | Config.LLM

    rewritten_question= rewrite_chain.invoke({"question": question}).strip()
    if not rewritten_question:
        return question
    return rewritten_question

def handle_answer_question(question):
    # Bộ đếm thời gian xử lý
    start_time = time.time()
    # Lấy danh sách NUMBER_CLOSEST_CHAT cuộc trò chuyện gần nhất
    chat_history = st.session_state.chat_history_ui[-Config.NUMBER_CLOSEST_CHAT:]

    # Nối danh sách lịch sử trò chuyện thành history_text
    history_text = "\n".join([
        f"User: {chat['content']}" if chat["role"] == "user" else f"AI: {chat['content']}"
        for chat in chat_history
    ])

    #Viết lại câu hỏi
    rewritten_question= call_llm_to_rewrite(history_text,question)
    print("Câu hỏi cũ: "+question)
    print("Câu hỏi mới: "+ rewritten_question)

    # Dùng retriever đã đưa vào session từ trước để truy xuất các chunk liên quan
    relevant_docs = st.session_state.retriever.invoke(rewritten_question)
    # Nối danh sách ngữ cảnh từ danh sách các chunk đã truy xuất
    context = "\n".join([doc.page_content for doc in relevant_docs])

    

    # Lưu câu hỏi user vào session
    st.session_state.chat_history_ui.append({
        "role": "user",
        "content": question,
        "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
    })

    # Kiểm tra question có phải tiếng việt không
    is_vietnamese = detect_is_vietnamese(question)
    
    # Generate prompt
    if is_vietnamese:
        prompt_template = get_vietnamese_template(history_text, context, question)
    else:
        prompt_template = get_english_template(history_text, context, question)
    
    # Nhận response từ promt
    response = Config.LLM.invoke(prompt_template)

    # Lấy ra thời gian xử lý
    elapsed_time = round(time.time() - start_time, 2)
    
    # ── Citation tracking: chuẩn bị sources data ──
    sources_data = [
        {
            "page":        doc.metadata.get('page', 0),
            "chunk_index": doc.metadata.get('chunk_index', '—'),
            "content":     doc.page_content,
        }
        for doc in relevant_docs
    ]
    keywords = extract_keywords(question)

    # Save assistant message (kèm sources + keywords)
    st.session_state.chat_history_ui.append({
        "role":          "ai",
        "content":       response,
        "timestamp":     datetime.datetime.now().strftime("%H:%M:%S"),
        "response_time": elapsed_time,
        "sources":       sources_data,
        "keywords":      keywords,
    })

# Stopwords tiếng Việt + tiếng Anh phổ biến (dùng để lọc từ khóa)
_STOPWORDS = {
    'là', 'và', 'của', 'có', 'trong', 'cho', 'được', 'với', 'này', 'các',
    'một', 'những', 'không', 'đã', 'về', 'từ', 'theo', 'đến', 'hay', 'như',
    'khi', 'tại', 'bởi', 'để', 'nếu', 'thì', 'mà', 'vì', 'sẽ', 'đó',
    'cũng', 'do', 'nào', 'ra', 'lại', 'rất', 'hơn', 'nhất', 'gì', 'ai',
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'shall', 'can', 'need', 'ought', 'used',
    'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as',
    'into', 'through', 'before', 'after', 'above', 'below', 'between',
    'out', 'off', 'over', 'under', 'again', 'then', 'once', 'here',
    'there', 'when', 'where', 'why', 'how', 'all', 'each', 'every',
    'both', 'few', 'more', 'most', 'other', 'some', 'no', 'nor', 'not',
    'only', 'same', 'so', 'than', 'too', 'very', 'and', 'but', 'or',
    'if', 'what', 'which', 'who', 'this', 'that', 'these', 'those',
    'i', 'me', 'my', 'we', 'our', 'you', 'your', 'he', 'him', 'his',
    'she', 'her', 'it', 'its', 'they', 'them', 'their',
}

def extract_keywords(question: str) -> list:
    """Tách từ khóa từ câu hỏi, loại bỏ stopwords và từ quá ngắn."""
    words = re.findall(r'[\w]+', question.lower())
    return [w for w in words if w not in _STOPWORDS and len(w) >= 2]
