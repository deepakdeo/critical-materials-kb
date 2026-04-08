"""Query endpoint for the RAG pipeline."""

import logging

from fastapi import APIRouter

from src.api.models import (
    QueryRequest,
    QueryResponseModel,
    SourceResponse,
    VerificationResponse,
)
from src.generation.chains import query as run_query

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/query", response_model=QueryResponseModel)
def query_endpoint(request: QueryRequest) -> QueryResponseModel:
    """Execute a RAG query and return a cited answer.

    Args:
        request: QueryRequest with question and optional filters.

    Returns:
        QueryResponseModel with answer, sources, verification, and metadata.
    """
    materials = request.filters.get("materials")
    doc_types = request.filters.get("doc_types")

    response = run_query(
        question=request.question,
        materials=materials,
        doc_types=doc_types,
    )

    sources = [
        SourceResponse(
            name=s.name,
            page=s.page,
            section=s.section,
            relevance_score=s.relevance_score,
        )
        for s in response.sources
    ]

    verification = VerificationResponse(
        verdict=response.verification.verdict,
        issues=response.verification.issues,
        severity=response.verification.severity,
    )

    return QueryResponseModel(
        answer=response.answer,
        sources=sources if request.include_sources else [],
        verification=verification,
        metadata=response.metadata,
    )
