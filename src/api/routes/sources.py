"""Sources endpoint for listing all document sources with URLs."""

from fastapi import APIRouter

from src.api.models import SourceDocumentResponse
from src.api.source_urls import get_all_sources

router = APIRouter()


@router.get("/sources", response_model=list[SourceDocumentResponse])
def list_sources() -> list[SourceDocumentResponse]:
    """Return all source documents with their public URLs."""
    return [
        SourceDocumentResponse(name=s["name"], url=s["url"])
        for s in get_all_sources()
    ]
