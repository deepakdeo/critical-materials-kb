"""Application configuration loaded from environment variables."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the critical-materials-kb application.

    All values can be overridden via environment variables or a .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM and Embeddings
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Database
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_service_key: str = ""

    # Knowledge Graph
    neo4j_uri: str = ""
    neo4j_user: str = ""
    neo4j_password: str = ""

    # Optional overrides
    cohere_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    llm_model: str = "claude-sonnet-4-20250514"
    reranker_model: str = "rerank-english-v3.0"

    # Chunking constants
    chunk_size_target: int = Field(default=750, description="Target chunk size in tokens")
    chunk_overlap: int = Field(
        default=100, description="Overlap between consecutive chunks in tokens"
    )

    # Embedding constants
    embedding_dimension: int = Field(default=1536, description="Dimension of embedding vectors")

    # Retrieval constants
    retrieval_top_k: int = Field(
        default=30, description="Number of candidates from initial retrieval"
    )
    rerank_top_k: int = Field(default=6, description="Number of candidates after reranking")
    rrf_k: int = Field(default=60, description="RRF constant k")


settings = Settings()
