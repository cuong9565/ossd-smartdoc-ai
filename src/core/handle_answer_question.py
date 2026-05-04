import streamlit as st
import time
import datetime
import re
from src.presistance.history_manager import save_messages
from .config import Config
from .prompt_template import detect_is_vietnamese, get_vietnamese_template, get_english_template
from ..advanced.benchmark_retrievers import benchmark_retriever
from .filtering import filter_documents

from langchain_core.prompts import PromptTemplate
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain.retrievers import ContextualCompressionRetriever
from src.advanced.hybrid_search import HybridRetriever

from .config import Config
from .prompt_template import detect_is_vietnamese, get_vietnamese_template, get_english_template, \
    rewrite_vietnamese_template


def _get_vector_retriever(use_rerank: bool, filters: dict = None):
    """Return Vector retriever, optionally wrapped with Cross-Encoder rerank."""
    vector_db = st.session_state.get("vector_db")
    if vector_db is None:
        raise RuntimeError("Vector DB chưa sẵn sàng. Vui lòng xử lý tài liệu trước.")

    k = int(st.session_state.get("retrieval_k") or 4)
    total_chunks = len(st.session_state.get("documents") or [])
    safe_k = min(total_chunks if total_chunks else k * 3, max(k * 3, k))
    
    search_kwargs = {"k": safe_k}
    if filters:
        actual_filters = {k: v for k, v in filters.items() if v}
        if actual_filters:
            search_kwargs["filter"] = lambda metadata: all(metadata.get(key) == val for key, val in actual_filters.items())

    base_retriever = vector_db.as_retriever(search_type="similarity", search_kwargs=search_kwargs)

    if not use_rerank:
        # return top-k later via base_retriever's k already; keep safe_k for better recall
        return base_retriever

    top_n = min(total_chunks if total_chunks else k, k)
    
    # Cache model to avoid reloading weights every time
    model = st.session_state.get("_cross_encoder_model")
    if model is None:
        model = HuggingFaceCrossEncoder(model_name="cross-encoder/mmarco-mMiniLMv2-L12-H384-v1")
        st.session_state["_cross_encoder_model"] = model
        
    compressor = CrossEncoderReranker(model=model, top_n=top_n)
    rerank_retriever = ContextualCompressionRetriever(
        base_compressor=compressor,
        base_retriever=base_retriever,
    )
    return rerank_retriever


def _get_hybrid_retriever(use_rerank: bool, filters: dict = None):
    """Return Hybrid retriever, rebuilding if rerank toggle changed or filters applied."""
    k = int(st.session_state.get("retrieval_k") or 4)
    docs = st.session_state.get("documents") or []
    if not docs:
        raise RuntimeError("Documents chưa sẵn sàng. Vui lòng xử lý tài liệu trước.")

    actual_filters = {k: v for k, v in filters.items() if v} if filters else {}
    
    if actual_filters:
        from .filtering import filter_documents
        docs = filter_documents(docs, 
            src=actual_filters.get("source"),
            file_type=actual_filters.get("file_type"),
            upload_date=actual_filters.get("upload_date")
        )
        if not docs:
            raise RuntimeError("Không có tài liệu nào khớp với bộ lọc hiện tại.")

    # Tận dụng cache nếu không có filter và thông số k/use_rerank không đổi
    if not actual_filters:
        r = st.session_state.get("hybrid_retriever")
        if r is not None and getattr(r, "use_rerank", None) == bool(use_rerank) and int(getattr(r, "top_k", k)) == k:
            return r

    # rebuild with proper toggle & wider candidate pools
    r = HybridRetriever(
        documents=docs,
        embedder=Config.get_embedder(),
        dense_k=max(30, k * 3),
        sparse_k=max(30, k * 3),
        rerank_k=max(30, k * 6),
        top_k=k,
        alpha=0.6,
        use_rerank=bool(use_rerank),
        reranker_model="cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
    )
    if not actual_filters:
        st.session_state.hybrid_retriever = r
    
    return r


def call_llm_to_rewrite(history_text: str, question: str) -> str:
    # Lấy thông tin hồ sơ tài liệu từ session state
    doc_profile = st.session_state.get("document_profile", "Không rõ lĩnh vực")

    # Xử lý chuỗi lịch sử nếu rỗng
    history_context = history_text if history_text.strip() else "Không có lịch sử hội thoại."

    # Khởi tạo template (Sử dụng chuỗi thô, không dùng f-string ở đây)
    template = rewrite_vietnamese_template()
    prompt = PromptTemplate(
        template=template,
        input_variables=["profile", "history", "question"],
    )

    rewrite_chain = prompt | Config.LLM

    # Truyền đầy đủ 3 tham số vào invoke để LangChain tự động điền vào template
    try:
        rewritten_question = rewrite_chain.invoke({
            "profile": doc_profile,
            "history": history_context,
            "question": question
        }).strip()
    except Exception:
        # Fallback nếu LLM gặp lỗi
        return question

    if not rewritten_question:
        return question

    return rewritten_question

def _build_history_text() -> str:
    """
    Xây dựng ngữ cảnh từ lịch sử chat gần nhất (để LLM hiểu ngữ cảnh).

    Lấy Config.NUMBER_CLOSEST_CHAT (mặc định 6 = 3 exchanges) message gần nhất,
    format thành "User: ... | AI: ..." để truyền vào prompt LLM.

    Bỏ qua dual messages (chế độ RAG + Graph RAG) vì chúng không có "content" trực tiếp.
    """
    chat_history = st.session_state.chat_history_ui[-Config.NUMBER_CLOSEST_CHAT:]
    result = []
    for chat in chat_history:
        # Bỏ qua dual messages (không có "content" trực tiếp)
        if chat.get("dual"):
            # Dùng nội dung từ RAG response cho history
            rag_content = chat.get("rag", {}).get("content", "")
            if rag_content:
                result.append(f"AI: {rag_content}")
        else:
            content = chat.get("content", "")
            if content:
                prefix = "User:" if chat["role"] == "user" else "AI:"
                result.append(f"{prefix} {content}")
    return "\n".join(result)


def _graph_context() -> str:
    """
    Xây dựng ngữ cảnh từ knowledge graph triples.

    Format: "subject | relation | object" cho mỗi triple
    Dùng các triple được trích xuất bằng spacy NER/dependency parsing.

    Return: Chuỗi text chứa tất cả triples (hoặc chuỗi rỗng nếu không có triple)
    """
    triples = st.session_state.get("graph_triples", []) or []
    if not triples:
        return ""
    return "\n".join([f"{subject} | {relation} | {object_}" for subject, relation, object_ in triples])


def _invoke_llm(question: str, context: str, history_text: str) -> str:
    """
    Gọi LLM (Qwen2.5 chạy local qua Ollama) với prompt đã tạo.

    Steps:
    1. Detect ngôn ngữ của câu hỏi (Tiếng Việt hay English)
    2. Chọn template prompt tương ứng
    3. Gọi Config.LLM.invoke() để lấy phản hồi

    Return: Phản hồi text từ LLM
    """
    is_vietnamese = detect_is_vietnamese(question)
    if is_vietnamese:
        prompt_template = get_vietnamese_template(history_text, context, question)
    else:
        prompt_template = get_english_template(history_text, context, question)
    return Config.LLM.invoke(prompt_template)


def _build_message(question: str, mode: str = "RAG", filters: dict = None) -> dict:
    """
    Xây dựng thông điệp phản hồi AI từ câu hỏi và mode truy xuất.

    Tùy mode RAG hoặc Graph RAG:
    - RAG: Dùng vector embeddings để tìm chunks liên quan nhất
    - Graph RAG: Tìm knowledge graph triples, fallback sang RAG nếu không có triples

    Return: dict với role, content, timestamp, response_time, sources, keywords, mode
    """
    start_time = time.time()
    use_graph_mode = False  # Track xem có dùng Graph RAG hay fallback RAG
    relevant_docs = []  # Lưu docs từ vector retriever

    # Tính toán lịch sử trước để sử dụng cho việc rewrite câu hỏi
    history_text = _build_history_text()

    # Viết lại câu hỏi
    rewritten_question = call_llm_to_rewrite(history_text, question)
    print("Câu hỏi cũ: " + question)
    print("Câu hỏi mới: " + rewritten_question)

    if mode == "Graph RAG":
        # Graph RAG: Tìm entity/relation triples từ tài liệu
        triples = st.session_state.get("graph_triples", []) or []
        if triples:
            # ✓ Có triples: dùng knowledge graph context cho LLM
            use_graph_mode = True
            context = _graph_context()
        else:
            # ✗ Không có triples: không fallback sang RAG, dùng context rỗng
            context = ""
    else:
        # RAG mode: Vector similarity search tìm chunks gần câu hỏi nhất
        if st.session_state.rag_mode["name"] is None:
            raise RuntimeError("Retriever chưa sẵn sàng. Vui lòng xử lý tài liệu trước.")

        # Choose Vector vs Hybrid retriever (default Vector)
        search_mode = (st.session_state.get("search_mode") or "Vector").lower()
        use_rerank = bool(st.session_state.get("use_rerank"))
        if search_mode == "hybrid":
            active_retriever = _get_hybrid_retriever(use_rerank, filters)
        else:
            active_retriever = _get_vector_retriever(use_rerank, filters)

        # Retrieval dùng câu hỏi đã rewrite (tăng recall cho cả Vector/BM25),
        # còn generation vẫn dùng câu hỏi gốc để giữ ý định giao tiếp.
        relevant_docs = active_retriever.invoke(rewritten_question)
        context = "\n".join([doc.page_content for doc in relevant_docs])

    # Gọi LLM với câu hỏi GỐC (để giữ ý định giao tiếp tự nhiên) nhưng context lấy từ câu hỏi viết lại
    response = _invoke_llm(question, context, history_text)
    elapsed_time = round(time.time() - start_time, 2)

    # Xây dựng sources để hiển thị trong UI
    # Nguồn trích dẫn format khác nhau tùy mode dùng
    if mode == "Graph RAG" and use_graph_mode:
        # Hiển thị triples dưới dạng: "subject | relation | object"
        sources_data = [
            {
                "page": None,
                "chunk_index": None,
                "content": " | ".join(triple),
            }
            for triple in triples
        ]
    else:
        # Hiển thị chunks với metadata (page number, chunk index trong trang)
        # Dùng cho cả RAG mode và Graph RAG fallback
        sources_data = [
            {
                "page": doc.metadata.get('page', 0),
                "chunk_index": doc.metadata.get('chunk_index', '—'),
                "content": doc.page_content,
            }
            for doc in relevant_docs
        ]

    # Extract keywords từ câu hỏi để highlight trong sources UI
    keywords = extract_keywords(question)

    return {
        "role": "ai",
        "content": response,
        "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
        "response_time": elapsed_time,
        "sources": sources_data,
        "keywords": keywords,
        "mode": mode,
    }


def handle_answer_question(question, mode=None, filters=None):
    """
    Xử lý một câu hỏi của user trong một mode RAG.

    Steps:
    1. Thêm câu hỏi vào chat history với role='user'
    2. Gọi _build_message để tạo phản hồi AI
    3. Thêm phản hồi vào chat history với role='ai'
    4. Return phản hồi
    """
    if not mode:
        mode = st.session_state.rag_mode["name"]
    user_msg = {
        "role" : "user",
        "content" : question,
        "response": "",
        "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
        "sources": [],
        "keywords": [],
    }
    # Ghi lại câu hỏi của user
    st.session_state.chat_history_ui.append(user_msg)
    save_messages(st.session_state.session_id, user_msg)
    # Xây dựng và ghi lại phản hồi AI
    answer_message = _build_message(question, mode, filters)
    answer_message["response"] = answer_message["content"]
    st.session_state.chat_history_ui.append(answer_message)

    
    save_messages(st.session_state.session_id, answer_message)
    return answer_message


def handle_benchmark_question(question: str, filters: dict = None):
    """
    Chạy benchmark so sánh Vector vs Hybrid cho 1 câu hỏi.
    Lưu kết quả vào chat history và SQLite để refresh vẫn xem lại được.
    """
    user_msg = {
        "role": "user",
        "content": question,
        "response": "",
        "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
        "sources": [],
        "keywords": [],
        "mode": "benchmark",
    }
    st.session_state.chat_history_ui.append(user_msg)
    save_messages(st.session_state.session_id, user_msg)

    docs = st.session_state.get("documents") or []
    actual_filters = {k: v for k, v in (filters or {}).items() if v}
    if actual_filters:
        docs = filter_documents(
            docs,
            src=actual_filters.get("source"),
            file_type=actual_filters.get("file_type"),
            upload_date=actual_filters.get("upload_date"),
        )
        if not docs:
            st.error("Không có tài liệu nào khớp với bộ lọc hiện tại.")
            return {}
    k = st.session_state.get("retrieval_k") or 4
    results = benchmark_retriever(
        questions=[question],
        documents=docs,
        retrieval_k=int(k),
    )
    row = results[0] if results else {}

    content = (
        "### Benchmark: Vector vs Hybrid\n\n"
        f"**Vector** (total: {row.get('pure_total_time')}s)\n\n{row.get('pure_answer','')}\n\n"
        f"**Hybrid** (total: {row.get('hybrid_total_time')}s)\n\n{row.get('hybrid_answer','')}"
    )
    ai_msg = {
        "role": "ai",
        "content": content,
        "response": content,
        "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
        "response_time": row.get("hybrid_total_time"),
        # Persist bench data inside sources so UI can render charts after reload
        "sources": [{"benchmark": row}],
        "keywords": [],
        "mode": "benchmark",
    }
    st.session_state.chat_history_ui.append(ai_msg)
    save_messages(st.session_state.session_id, ai_msg)
    return row


def handle_answer_question_multi(question):
    """
    So sánh phản hồi RAG vs Graph RAG khi chế độ kết hợp được chọn.

    Chạy tuần tự (không dùng thread) để tránh race condition trên Streamlit session_state:
    1. Thêm user question vào chat history
    2. Gọi _build_message cho "RAG" mode
    3. Gọi _build_message cho "Graph RAG" mode
    4. Thêm một phản hồi dual vào chat history
    5. Return dict {"RAG": msg1, "Graph RAG": msg2} để UI hiển thị side-by-side
    """

    user_msg = {
        "role": "user",
        "content": question,
        "response": "",
        "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
        "sources": [],
        "keywords": [],
    }
    st.session_state.chat_history_ui.append(user_msg)

    # Chạy tuần tự thay vì dùng ThreadPoolExecutor để tránh rủi ro race condition
    # (Streamlit session_state không an toàn khi đọc từ nhiều thread)
    rag_message = _build_message(question, "RAG")
    graph_message = _build_message(question, "Graph RAG")

    # Thêm một message dual
    dual_message = {
        "role": "ai",
        "dual": True,
        "rag": rag_message,
        "graph": graph_message,
        "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
        "content": f"RAG: {rag_message['content']}\n\nGraph: {graph_message['content']}",
        "response": f"RAG: {rag_message['content']}\n\nGraph: {graph_message['content']}",
        "sources": rag_message.get("sources", []),
        "keywords": rag_message.get("keywords", [])
    }
    st.session_state.chat_history_ui.append(dual_message)
    save_messages(st.session_state.session_id, dual_message)

    return {"RAG": rag_message, "Graph RAG": graph_message}


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
    """
    Tách từ khóa từ câu hỏi (loại bỏ stopwords và từ quá ngắn).

    Dùng để highlight các từ quan trọng trong sources UI.
    - Áp dụng regex để lấy từ (word characters)
    - Loại bỏ stopwords tiếng Việt và tiếng Anh
    - Loại bỏ các từ có độ dài < 2 ký tự

    Return: list của các từ khóa duy nhất (lowercase)
    """
    words = re.findall(r'[\w]+', question.lower())
    return [w for w in words if w not in _STOPWORDS and len(w) >= 2]