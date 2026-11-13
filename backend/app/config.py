from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    VECTOR_STORE: str = "qdrant"
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION_PREFIX: str = "rv_"
    CHROMA_PATH: str = "./chroma_data"
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    LLM_PROVIDER: str = "openai"
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    MAX_UPLOAD_SIZE_MB: int = 25
    DATABASE_URL: str = "sqlite:///./researchvault.db"
    RETRIEVAL_TOP_K: int = 20
    RERANK_TOP_K: int = 5
    SIMILARITY_THRESHOLD: float = 0.3
    ENABLE_HYBRID_SEARCH: bool = False
    ENABLE_RERANKING: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
