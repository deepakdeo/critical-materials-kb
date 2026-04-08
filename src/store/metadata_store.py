"""Document metadata CRUD operations against the Supabase documents table."""

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


def create_document(
    name: str,
    document_type: str,
    file_path: str,
    file_hash: str,
    total_chunks: int,
    materials: list[str] | None = None,
    source_url: str = "",
    date_published: str | None = None,
    metadata: dict | None = None,
) -> dict[str, Any]:
    """Create a new document record in the documents table.

    Args:
        name: Document name (usually the filename).
        document_type: Type of document (e.g., 'usgs_mcs', 'gao_report').
        file_path: Local file path of the source document.
        file_hash: SHA-256 hash of the file for deduplication.
        total_chunks: Number of chunks produced from this document.
        materials: Optional list of materials mentioned.
        source_url: Optional URL where the document can be found.
        date_published: Optional publication date (YYYY-MM-DD string).
        metadata: Optional additional metadata.

    Returns:
        The created document record as a dictionary.
    """
    client = _get_client()

    row: dict[str, Any] = {
        "name": name,
        "document_type": document_type,
        "file_path": file_path,
        "file_hash": file_hash,
        "total_chunks": total_chunks,
        "materials": materials or [],
        "metadata": metadata or {},
    }

    if source_url:
        row["source_url"] = source_url
    if date_published:
        row["date_published"] = date_published

    result = client.table("documents").insert(row).execute()
    doc = result.data[0]
    logger.info("Created document record: %s (id=%s)", name, doc.get("id"))
    return doc


def get_document(document_id: str) -> dict[str, Any] | None:
    """Retrieve a document record by ID.

    Args:
        document_id: UUID of the document.

    Returns:
        The document record as a dictionary, or None if not found.
    """
    client = _get_client()
    result = client.table("documents").select("*").eq("id", document_id).execute()
    if result.data:
        return result.data[0]
    return None


def get_document_by_hash(file_hash: str) -> dict[str, Any] | None:
    """Retrieve a document record by file hash.

    Args:
        file_hash: SHA-256 hash of the file.

    Returns:
        The document record as a dictionary, or None if not found.
    """
    client = _get_client()
    result = client.table("documents").select("*").eq("file_hash", file_hash).execute()
    if result.data:
        return result.data[0]
    return None


def list_documents(
    document_type: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """List document records, optionally filtered by type.

    Args:
        document_type: Optional filter by document type.
        limit: Maximum number of records to return.

    Returns:
        List of document records.
    """
    client = _get_client()
    query = client.table("documents").select("*").limit(limit).order("ingested_at", desc=True)

    if document_type:
        query = query.eq("document_type", document_type)

    result = query.execute()
    return result.data


def delete_document(document_id: str) -> bool:
    """Delete a document record and its associated chunks (via CASCADE).

    Args:
        document_id: UUID of the document to delete.

    Returns:
        True if the document was deleted, False if it was not found.
    """
    client = _get_client()
    result = client.table("documents").delete().eq("id", document_id).execute()
    deleted = len(result.data) > 0
    if deleted:
        logger.info("Deleted document %s", document_id)
    else:
        logger.warning("Document %s not found for deletion", document_id)
    return deleted
