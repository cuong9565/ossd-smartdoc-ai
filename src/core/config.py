from langchain_community.embeddings import HuggingFaceEmbeddings              # biến text -> vector
from langchain_ollama import OllamaLLM                               # gọi LLM chạy local

class Config:
    # Embedding
    EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

    # Embedder
    EMBEDDER = HuggingFaceEmbeddings(
        model_name = EMBEDDING_MODEL,
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )

    # LLM
    LLM = OllamaLLM(
        model="qwen2.5:7b",
        temperature=0.7,
        top_p=0.9,
        repeat_penalty=1.1,
    )

    # Number closet chat: Biến lưu số lượng cuộc trò chuyện muốn dùng gần nhất ra làm ngữ cảnh
    # Lấy gấp đôi vì trong chat có 2 role là user và ai
    NUMBER_CLOSEST_CHAT = 3 * 2