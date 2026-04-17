from functools import lru_cache

import torch
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_ollama import OllamaLLM


class Config:
    EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

    @classmethod
    @lru_cache(maxsize=1)
    def get_device(cls):
        # Ưu tiên GPU nếu máy có CUDA, không thì fallback về CPU.
        return "cuda" if torch.cuda.is_available() else "cpu"

    @classmethod
    @lru_cache(maxsize=1)
    def get_embedder(cls):
        device = cls.get_device()
        print(f"[SmartDoc] Embedding device: {device}")

        return HuggingFaceEmbeddings(
            model_name=cls.EMBEDDING_MODEL,
            model_kwargs={"device": device},
            encode_kwargs={"normalize_embeddings": True},
        )

    @classmethod
    @lru_cache(maxsize=1)
    def get_llm(cls):
        print("[SmartDoc] LLM: Ollama local")
        return OllamaLLM(
            model="qwen2.5:7b",
            temperature=0.7,
            top_p=0.9,
            repeat_penalty=1.1,
        )

    # Lấy 3 lượt chat gần nhất, mỗi lượt gồm user + ai
    NUMBER_CLOSEST_CHAT = 3 * 2