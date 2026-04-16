from core.config import Config
from langchain_ollama import OllamaLLM

def get_llm():
    return OllamaLLM(model=Config.LLM_MODEL)