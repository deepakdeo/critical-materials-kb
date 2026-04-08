"""Supabase full-text search (BM25) operations using tsvector."""

import logging
from typing import Any

from src.config import settings
from supabase import Client, create_client

logger = logging.getLogger(__name__)

_client: Client | None = None


def _get_client() -> Client:
    """Get or create a Supabase client."""
    global _client
    if _client is None:
        _client = create_client(settings.supabase_url, settings.supabase_service_key)
    return _client


def search(
    query: str,
    top_k: int | None = None,
    materials: list[str] | None = None,
    doc_type: str | None = None,
) -> list[dict[str, Any]]:
    """Perform full-text search on the chunks table using tsvector.

    Uses a Supabase RPC function `fts_search_chunks` that wraps the query
    with plainto_tsquery and ranks results using ts_rank.

    Args:
        query: The search query string.
        top_k: Number of results to return (defaults to settings.retrieval_top_k).
        materials: Optional filter — only return chunks mentioning these materials.
        doc_type: Optional filter — only return chunks from this document type.

    Returns:
        List of matching chunk records with relevance scores.
    """
    client = _get_client()
    k = top_k or settings.retrieval_top_k

    params: dict[str, Any] = {
        "search_query": query,
        "match_count": k,
    }

    if materials:
        params["filter_materials"] = materials
    if doc_type:
        params["filter_doc_type"] = doc_type

    result = client.rpc("fts_search_chunks", params).execute()
    logger.debug("Full-text search returned %d results for query: '%s'", len(result.data), query)
    return result.data
