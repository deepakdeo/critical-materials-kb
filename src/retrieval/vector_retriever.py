"""Semantic similarity search via Supabase pgvector."""

import logging
from typing import Any

from pydantic import BaseModel, Field

from src.config import settings
from src.ingest.embedder import embed_texts
from src.store.vector_store import similarity_search

logger = logging.getLogger(__name__)


class RetrievalResult(BaseModel):
    """Standardized result from any retrieval module."""

    chunk_id: str = ""
    document_id: str = ""
    text: str = ""
    section_title: str = ""
    page_numbers: list[int] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    score: float = 0.0
    source: str = ""  # "vector", "bm25", "hybrid", "graph"


def vector_search(
    query: str,
    top_k: int | None = None,
    materials: list[str] | None = None,
    doc_type: str | None = None,
) -> list[RetrievalResult]:
    """Perform semantic similarity search using pgvector.

    Embeds the query text, then searches for the most similar chunks
    in the vector store using cosine similarity.

    Args:
        query: The search query string.
        top_k: Number of results to return.
        materials: Optional filter by materials mentioned.
        doc_type: Optional filter by document type.

    Returns:
        List of RetrievalResult sorted by similarity score descending.
    """
    k = top_k or settings.retrieval_top_k

    # Embed the query
    embeddings = embed_texts([query])
    if not embeddings:
        logger.warning("Failed to embed query: '%s'", query)
        return []

    query_embedding = embeddings[0]

    # Search
    raw_results = similarity_search(
        query_embedding=query_embedding,
        top_k=k,
        materials=materials,
        doc_type=doc_type,
    )

    results = []
    for row in raw_results:
        results.append(RetrievalResult(
            chunk_id=str(row.get("id", "")),
            document_id=str(row.get("document_id", "")),
            text=row.get("text", ""),
            section_title=row.get("section_title", ""),
            page_numbers=row.get("page_numbers", []),
            materials=row.get("materials", []),
            metadata=row.get("metadata", {}),
            score=float(row.get("similarity", 0.0)),
            source="vector",
        ))

    logger.info("Vector search returned %d results for: '%s'", len(results), query[:80])
    return results
