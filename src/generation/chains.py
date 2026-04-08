"""End-to-end retrieval → generation → verification chain."""

import logging
import time
from typing import Any

from pydantic import BaseModel, Field

from src.generation.generator import generate_answer
from src.generation.verifier import VerificationResult, verify_answer
from src.retrieval.hybrid_retriever import hybrid_search
from src.retrieval.query_classifier import QueryType, classify_query
from src.retrieval.reranker import rerank
from src.retrieval.vector_retriever import RetrievalResult

logger = logging.getLogger(__name__)


class SourceReference(BaseModel):
    """A source document reference in the query response."""

    name: str = ""
    page: str = ""
    section: str = ""
    relevance_score: float = 0.0


class QueryResponse(BaseModel):
    """Complete response from the RAG pipeline."""

    answer: str = ""
    sources: list[SourceReference] = Field(default_factory=list)
    verification: VerificationResult = Field(default_factory=VerificationResult)
    metadata: dict[str, Any] = Field(default_factory=dict)


def _build_sources(chunks: list[RetrievalResult]) -> list[SourceReference]:
    """Extract source references from reranked chunks."""
    sources = []
    seen = set()
    for chunk in chunks:
        source_name = chunk.metadata.get("source_name", "Unknown")
        pages = chunk.page_numbers
        page_str = f"p.{','.join(str(p) for p in pages)}" if pages else ""
        key = f"{source_name}:{page_str}"
        if key not in seen:
            seen.add(key)
            sources.append(SourceReference(
                name=source_name,
                page=page_str,
                section=chunk.section_title or "",
                relevance_score=round(chunk.score, 4),
            ))
    return sources


def query(
    question: str,
    materials: list[str] | None = None,
    doc_types: list[str] | None = None,
) -> QueryResponse:
    """Execute the full RAG pipeline: classify → retrieve → rerank → generate → verify.

    Args:
        question: The user's natural language question.
        materials: Optional material filters.
        doc_types: Optional document type filters.

    Returns:
        QueryResponse with answer, sources, verification, and metadata.
    """
    start_time = time.time()

    # Step 1: Classify query
    query_type = classify_query(question)

    # Step 2: Determine doc_type filter from classification
    doc_type_filter = None
    if query_type == QueryType.REGULATORY and not doc_types:
        doc_type_filter = "regulatory"
    elif doc_types and len(doc_types) == 1:
        doc_type_filter = doc_types[0]

    # Step 3: Hybrid retrieval
    hybrid_results = hybrid_search(
        query=question,
        materials=materials,
        doc_type=doc_type_filter,
    )
    chunks_retrieved = len(hybrid_results)

    # Step 4: Cross-encoder reranking
    reranked = rerank(query=question, results=hybrid_results)
    chunks_after_rerank = len(reranked)

    # Step 5: Generate answer
    answer = generate_answer(question=question, chunks=reranked)

    # Step 6: Verify answer (CRAG)
    verification = verify_answer(answer=answer, chunks=reranked)

    # Step 7: If major failure, retry once with re-retrieval
    if verification.verdict == "FAIL" and verification.severity == "major":
        logger.warning(
            "Verification FAILED (major) — retrying with broader retrieval"
        )
        # Retry with more candidates
        hybrid_results_retry = hybrid_search(
            query=question,
            top_k=50,
            materials=materials,
        )
        reranked_retry = rerank(
            query=question, results=hybrid_results_retry, top_k=10
        )
        answer = generate_answer(question=question, chunks=reranked_retry)
        verification = verify_answer(answer=answer, chunks=reranked_retry)

        # If still failing, return "insufficient data"
        if verification.verdict == "FAIL" and verification.severity == "major":
            answer = (
                "The available documents do not contain sufficient information "
                "to answer this question with the required level of confidence. "
                f"Verification issues: {'; '.join(verification.issues)}"
            )
            reranked = reranked_retry
            chunks_after_rerank = len(reranked)

    # Build response
    elapsed_ms = int((time.time() - start_time) * 1000)
    sources = _build_sources(reranked)

    response = QueryResponse(
        answer=answer,
        sources=sources,
        verification=verification,
        metadata={
            "query_type": query_type.value,
            "retrieval_method": "hybrid",
            "chunks_retrieved": chunks_retrieved,
            "chunks_after_rerank": chunks_after_rerank,
            "latency_ms": elapsed_ms,
        },
    )

    logger.info(
        "Query pipeline complete: type=%s, chunks=%d→%d, verified=%s, %dms",
        query_type.value,
        chunks_retrieved,
        chunks_after_rerank,
        verification.verdict,
        elapsed_ms,
    )
    return response
