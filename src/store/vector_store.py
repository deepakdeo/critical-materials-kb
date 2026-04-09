"""Supabase pgvector operations for chunk storage and similarity search."""

import logging
from typing import Any

from src.config import settings
from src.ingest.chunker import Chunk
from supabase import Client, create_client

logger = logging.getLogger(__name__)

_client: Client | None = None


def _get_client() -> Client:
    """Get or create a Supabase client."""
    global _client
    if _client is None:
        _client = create_client(settings.supabase_url, settings.supabase_service_key)
    return _client


def upsert_chunks(chunks: list[Chunk], document_id: str) -> int:
    """Batch insert chunks with embeddings into the chunks table.

    Args:
        chunks: List of Chunk models with embeddings attached.
        document_id: UUID of the parent document record.

    Returns:
        Number of chunks inserted.

    Raises:
        ValueError: If any chunk is missing an embedding.
    """
    if not chunks:
        return 0

    client = _get_client()
    rows: list[dict[str, Any]] = []

    for chunk in chunks:
        if chunk.embedding is None:
            raise ValueError(f"Chunk {chunk.chunk_index} is missing an embedding")

        rows.append({
            "document_id": document_id,
            "chunk_index": chunk.chunk_index,
            "text": chunk.text,
            "section_title": chunk.section_title,
            "page_numbers": chunk.page_numbers,
            "materials": chunk.materials,
            "embedding": chunk.embedding,
            "metadata": {
                "source_name": chunk.source_name,
                "document_type": chunk.document_type,
                "total_chunks_in_doc": chunk.total_chunks_in_doc,
            },
        })

    # Insert in batches of 50 to stay within payload limits
    batch_size = 50
    inserted = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        result = client.table("chunks").insert(batch).execute()
        inserted += len(result.data)

    logger.info("Inserted %d chunks for document %s", inserted, document_id)
    return inserted


def similarity_search(
    query_embedding: list[float],
    top_k: int | None = None,
    materials: list[str] | None = None,
    doc_type: str | None = None,
) -> list[dict[str, Any]]:
    """Search for similar chunks using pgvector cosine similarity.

    Uses a Supabase RPC function `match_chunks` that performs the vector search.

    Args:
        query_embedding: The query embedding vector.
        top_k: Number of results to return (defaults to settings.retrieval_top_k).
        materials: Optional filter — only return chunks mentioning these materials.
        doc_type: Optional filter — only return chunks from this document type.

    Returns:
        List of matching chunk records with similarity scores.
    """
    client = _get_client()
    k = top_k or settings.retrieval_top_k

    params: dict[str, Any] = {
        "query_embedding": query_embedding,
        "match_count": k,
    }

    if materials:
        params["filter_materials"] = materials
    if doc_type:
        params["filter_doc_type"] = doc_type

    result = client.rpc("match_chunks", params).execute()
    logger.debug("Vector search returned %d results", len(result.data))
    return result.data


def get_chunks_by_document_id(
    document_id: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Fetch the first N chunks for a given document, ordered by chunk_index.

    Used by the doc-title boost path in hybrid retrieval to seed the
    candidate pool with chunks from a specifically-named document.

    Args:
        document_id: UUID of the parent document.
        limit: Maximum chunks to return.

    Returns:
        List of chunk records (same shape as similarity_search results).
    """
    client = _get_client()
    result = (
        client.table("chunks")
        .select("*")
        .eq("document_id", document_id)
        .order("chunk_index")
        .limit(limit)
        .execute()
    )
    return result.data


def delete_by_document_id(document_id: str) -> int:
    """Delete all chunks belonging to a document.

    Args:
        document_id: UUID of the document whose chunks should be deleted.

    Returns:
        Number of chunks deleted.
    """
    client = _get_client()
    result = client.table("chunks").delete().eq("document_id", document_id).execute()
    count = len(result.data)
    logger.info("Deleted %d chunks for document %s", count, document_id)
    return count
