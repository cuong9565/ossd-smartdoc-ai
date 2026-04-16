from langchain_community.embeddings import HuggingFaceEmbeddings              # biến text -> vector

class Config:
    # Embedding
    EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

    # Embedder
    EMBEDDER = HuggingFaceEmbeddings(
        model_name = EMBEDDING_MODEL,
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )