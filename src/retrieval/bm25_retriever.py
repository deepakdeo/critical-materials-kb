"""Keyword/exact-match search via Supabase full-text search (BM25/tsvector)."""

import logging

from src.config import settings
from src.retrieval.vector_retriever import RetrievalResult
from src.store.fulltext_store import search as fts_search

logger = logging.getLogger(__name__)


def bm25_search(
    query: str,
    top_k: int | None = None,
    materials: list[str] | None = None,
    doc_type: str | None = None,
) -> list[RetrievalResult]:
    """Perform full-text search using Supabase tsvector with ts_rank scoring.

    Args:
        query: The search query string.
        top_k: Number of results to return.
        materials: Optional filter by materials mentioned.
        doc_type: Optional filter by document type.

    Returns:
        List of RetrievalResult sorted by BM25 rank descending.
    """
    k = top_k or settings.retrieval_top_k

    raw_results = fts_search(
        query=query,
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
            score=float(row.get("rank", 0.0)),
            source="bm25",
        ))

    logger.info("BM25 search returned %d results for: '%s'", len(results), query[:80])
    return results
