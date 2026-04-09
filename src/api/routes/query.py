"""Query endpoint for the RAG pipeline."""

import logging

from fastapi import APIRouter, Depends

from src.api.models import (
    QueryRequest,
    QueryResponseModel,
    SourceResponse,
    VerificationResponse,
)
from src.api.rate_limit import check_rate_limit
from src.generation.chains import query as run_query

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/query",
    response_model=QueryResponseModel,
    dependencies=[Depends(check_rate_limit)],
)
def query_endpoint(request: QueryRequest) -> QueryResponseModel:
    """Execute a RAG query and return a cited answer.

    Args:
        request: QueryRequest with question and optional filters.

    Returns:
        QueryResponseModel with answer, sources, verification, and metadata.
    """
    materials = request.filters.get("materials")
    doc_types = request.filters.get("doc_types")

    # Build conversation context for multi-turn
    context = None
    if request.conversation_context:
        context = [
            {"question": t.question, "answer": t.answer}
            for t in request.conversation_context
        ]

    response = run_query(
        question=request.question,
        materials=materials,
        doc_types=doc_types,
        conversation_context=context,
    )

    sources = [
        SourceResponse(
            name=s.name,
            page=s.page,
            section=s.section,
            relevance_score=s.relevance_score,
            chunk_text=s.chunk_text,
            source_url=s.source_url,
        )
        for s in response.sources
    ] if request.include_sources else []

    verification = VerificationResponse(
        verdict=response.verification.verdict,
        issues=response.verification.issues,
        severity=response.verification.severity,
    )

    return QueryResponseModel(
        answer=response.answer,
        sources=sources,
        verification=verification,
        metadata=response.metadata,
        follow_up_questions=response.follow_up_questions,
        graph_data=response.graph_data,
    )
