"""Health check endpoint."""

import logging

from fastapi import APIRouter

from src.api.models import HealthResponse
from src.store.metadata_store import list_documents

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Return system health status with document and chunk counts."""
    try:
        docs = list_documents(limit=1000)
        doc_count = len(docs)
        chunk_count = sum(d.get("total_chunks", 0) or 0 for d in docs)
        return HealthResponse(
            status="ok",
            document_count=doc_count,
            chunk_count=chunk_count,
        )
    except Exception as e:
        logger.error("Health check failed: %s", e)
        return HealthResponse(status=f"error: {e}")
