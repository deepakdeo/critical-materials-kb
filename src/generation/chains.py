"""End-to-end retrieval → generation → verification chain."""

import logging
import time
from typing import Any

from pydantic import BaseModel, Field

from src.api.source_urls import get_source_url_with_page
from src.generation.generator import generate_answer, generate_fallback_answer
from src.generation.verifier import VerificationResult, verify_answer
from src.retrieval.graph_retriever import graph_search
from src.retrieval.hybrid_retriever import hybrid_search
from src.retrieval.query_classifier import QueryType, classify_query
from src.retrieval.reranker import rerank
from src.retrieval.vector_retriever import RetrievalResult
from src.store.query_cache import (
    get_cached_response,
    make_cache_key,
    set_cached_response,
)

logger = logging.getLogger(__name__)


class SourceReference(BaseModel):
    """A source document reference in the query response."""

    name: str = ""
    page: str = ""
    section: str = ""
    relevance_score: float = 0.0
    chunk_text: str = ""
    source_url: str | None = None


class GraphNode(BaseModel):
    """A node in the knowledge graph visualization."""

    id: str
    label: str
    type: str  # Material, Company, Country, etc.


class GraphEdge(BaseModel):
    """An edge in the knowledge graph visualization."""

    source: str
    target: str
    label: str  # PRODUCES, DEPENDS_ON, etc.


class QueryResponse(BaseModel):
    """Complete response from the RAG pipeline."""

    answer: str = ""
    sources: list[SourceReference] = Field(default_factory=list)
    verification: VerificationResult = Field(default_factory=VerificationResult)
    metadata: dict[str, Any] = Field(default_factory=dict)
    follow_up_questions: list[str] = Field(default_factory=list)
    graph_data: dict[str, Any] = Field(default_factory=dict)


def _build_sources(chunks: list[RetrievalResult]) -> list[SourceReference]:
    """Extract source references from reranked chunks."""
    sources = []
    seen = set()
    for chunk in chunks:
        source_name = chunk.metadata.get("source_name", "Unknown")
        pages = chunk.page_numbers
        page_str = (
            f"p.{','.join(str(p) for p in pages)}" if pages else ""
        )
        key = f"{source_name}:{page_str}"
        if key not in seen:
            seen.add(key)
            sources.append(SourceReference(
                name=source_name,
                page=page_str,
                section=chunk.section_title or "",
                relevance_score=round(chunk.score, 4),
                chunk_text=chunk.text[:500] if chunk.text else "",
                source_url=get_source_url_with_page(source_name, pages),
            ))
    return sources


def _extract_graph_data(
    graph_results: list[RetrievalResult],
) -> dict[str, Any]:
    """Extract graph nodes and edges from graph retrieval results.

    Parses the formatted text from graph_retriever to build
    a visualization-friendly structure.
    """
    if not graph_results:
        return {"nodes": [], "edges": []}

    nodes: dict[str, GraphNode] = {}
    edges: list[GraphEdge] = []

    for result in graph_results:
        text = result.text

        # Parse lines like "company: X | role: PRODUCES | material: Y"
        for line in text.split("\n"):
            line = line.strip()
            if not line.startswith("- "):
                continue
            line = line[2:]

            fields = {}
            for part in line.split(" | "):
                if ": " in part:
                    k, v = part.split(": ", 1)
                    fields[k.strip()] = v.strip()

            # Build nodes and edges from parsed fields
            if "company" in fields and "material" in fields:
                comp = fields["company"]
                mat = fields["material"]
                rel = fields.get("relationship", fields.get("role", "RELATED"))
                if comp and comp != "None":
                    nodes[comp] = GraphNode(
                        id=comp, label=comp, type="Company"
                    )
                if mat and mat != "None":
                    nodes[mat] = GraphNode(
                        id=mat, label=mat, type="Material"
                    )
                if comp and mat and comp != "None" and mat != "None":
                    edges.append(GraphEdge(
                        source=comp, target=mat, label=rel
                    ))

            if "weapon_system" in fields and "material" in fields:
                ws = fields["weapon_system"]
                mat = fields["material"]
                if ws and ws != "None":
                    nodes[ws] = GraphNode(
                        id=ws, label=ws, type="WeaponSystem"
                    )
                if mat and mat != "None":
                    nodes[mat] = GraphNode(
                        id=mat, label=mat, type="Material"
                    )
                if ws and mat and ws != "None" and mat != "None":
                    edges.append(GraphEdge(
                        source=ws, target=mat, label="DEPENDS_ON"
                    ))

            if "country" in fields and "material" in fields:
                co = fields["country"]
                mat = fields["material"]
                rel = fields.get("role", "PRODUCES")
                if co and co != "None":
                    nodes[co] = GraphNode(
                        id=co, label=co, type="Country"
                    )
                if mat and mat != "None":
                    nodes[mat] = GraphNode(
                        id=mat, label=mat, type="Material"
                    )
                if co and mat and co != "None" and mat != "None":
                    edges.append(GraphEdge(
                        source=co, target=mat, label=rel
                    ))

            if "award" in fields:
                award = fields["award"]
                company = fields.get("company", "")
                mat = fields.get("material", "")
                if award and award != "None":
                    nodes[award] = GraphNode(
                        id=award, label=award, type="DPAAward"
                    )
                if company and company != "None":
                    nodes[company] = GraphNode(
                        id=company, label=company, type="Company"
                    )
                    edges.append(GraphEdge(
                        source=award, target=company, label="AWARDED_TO"
                    ))
                if mat and mat != "None":
                    edges.append(GraphEdge(
                        source=award, target=mat, label="FUNDS"
                    ))

            if "regulation" in fields and "material" in fields:
                reg = fields["regulation"]
                mat = fields["material"]
                if reg and reg != "None":
                    nodes[reg] = GraphNode(
                        id=reg, label=reg, type="Regulation"
                    )
                if mat and mat != "None":
                    nodes[mat] = GraphNode(
                        id=mat, label=mat, type="Material"
                    )
                if reg and mat and reg != "None" and mat != "None":
                    edges.append(GraphEdge(
                        source=reg, target=mat, label="REGULATES"
                    ))

    # Deduplicate edges by (source, target, label)
    seen_edges: set[tuple[str, str, str]] = set()
    unique_edges: list[GraphEdge] = []
    for e in edges:
        key = (e.source, e.target, e.label)
        if key not in seen_edges:
            seen_edges.add(key)
            unique_edges.append(e)

    return {
        "nodes": [n.model_dump() for n in nodes.values()],
        "edges": [e.model_dump() for e in unique_edges],
    }


def _generate_follow_ups(
    question: str, answer: str, query_type: str,
) -> list[str]:
    """Generate follow-up question suggestions."""
    try:
        from anthropic import Anthropic

        from src.config import settings

        client = Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model=settings.llm_model,
            max_tokens=200,
            temperature=0,
            messages=[{
                "role": "user",
                "content": (
                    "Based on this Q&A about U.S. critical materials "
                    "supply chains, suggest exactly 3 brief follow-up "
                    "questions the user might want to ask next. Return "
                    "ONLY the 3 questions, one per line, no numbering "
                    "or bullets.\n\n"
                    f"Question: {question}\n\n"
                    f"Answer summary: {answer[:300]}\n\n"
                    f"Query type: {query_type}"
                ),
            }],
        )
        raw = response.content[0].text.strip()
        questions = [
            q.strip().lstrip("0123456789.-) ")
            for q in raw.split("\n") if q.strip()
        ]
        return questions[:3]
    except Exception as e:
        logger.warning("Follow-up generation failed: %s", e)
        return []


def _compute_confidence(
    verification: VerificationResult,
    chunks_after_rerank: int,
    retrieval_method: str,
) -> float:
    """Compute a confidence score 0-1 for the answer."""
    score = 0.5

    # Verification result
    if verification.verdict == "PASS":
        score += 0.3
        if verification.severity == "none":
            score += 0.1
    elif verification.severity == "minor":
        score += 0.1

    # More reranked chunks = more evidence
    if chunks_after_rerank >= 4:
        score += 0.05
    if chunks_after_rerank >= 6:
        score += 0.05

    # Graph enrichment boosts confidence for relational queries
    if "graph" in retrieval_method:
        score += 0.05

    return min(score, 1.0)


def query(
    question: str,
    materials: list[str] | None = None,
    doc_types: list[str] | None = None,
    conversation_context: list[dict] | None = None,
) -> QueryResponse:
    """Execute the full RAG pipeline.

    Args:
        question: The user's natural language question.
        materials: Optional material filters.
        doc_types: Optional document type filters.
        conversation_context: Optional prior Q&A pairs for multi-turn.

    Returns:
        QueryResponse with answer, sources, verification, and metadata.
    """
    start_time = time.time()

    # Cache lookup — keyed on (question, filters) only, ignoring
    # conversation_context. If someone re-asks the same standalone
    # question mid-conversation, they should get the same fast cached
    # answer. Truly context-dependent follow-ups ("tell me more",
    # "what about nickel?") naturally have different question text and
    # therefore different cache keys.
    cache_key = make_cache_key(question, materials, doc_types)
    cached = get_cached_response(cache_key)
    if cached is not None:
        logger.info("Cache HIT: %s", question[:80])
        cached_response = QueryResponse(**cached)
        cached_response.metadata["from_cache"] = True
        cached_response.metadata["latency_ms"] = int(
            (time.time() - start_time) * 1000
        )
        return cached_response

    # Enrich question with conversation context for multi-turn
    enriched_question = question
    if conversation_context:
        context_parts = []
        for turn in conversation_context[-3:]:  # Last 3 turns max
            context_parts.append(
                f"Previous Q: {turn.get('question', '')}\n"
                f"Previous A summary: {turn.get('answer', '')[:200]}"
            )
        enriched_question = (
            "Context from previous conversation:\n"
            + "\n---\n".join(context_parts)
            + f"\n\nCurrent question: {question}"
        )

    # Step 1: Classify query
    query_type = classify_query(question)
    is_fallback = False

    # Step 2: Determine doc_type filter
    doc_type_filter = None
    if doc_types and len(doc_types) == 1:
        doc_type_filter = doc_types[0]

    # Step 3: Graph retrieval
    graph_results: list[RetrievalResult] = []
    retrieval_method = "hybrid"
    if query_type in (
        QueryType.RELATIONAL, QueryType.ANALYTICAL, QueryType.REGULATORY
    ):
        try:
            graph_results = graph_search(question)
            if graph_results:
                retrieval_method = "hybrid+graph"
        except Exception as e:
            logger.warning("Graph retrieval failed: %s", e)

    # Step 4: Hybrid retrieval
    hybrid_results = hybrid_search(
        query=enriched_question,
        materials=materials,
        doc_type=doc_type_filter,
    )

    combined_results = graph_results + hybrid_results
    chunks_retrieved = len(combined_results)

    # Step 5: Cross-encoder reranking
    reranked = rerank(query=question, results=combined_results)
    chunks_after_rerank = len(reranked)

    # Step 6: Generate answer
    answer = generate_answer(question=enriched_question, chunks=reranked)

    # Step 7: Verify answer (CRAG)
    verification = verify_answer(answer=answer, chunks=reranked)

    # Step 8: Retry on major failure
    if verification.verdict == "FAIL" and verification.severity == "major":
        logger.warning("Verification FAILED (major) — retrying")
        hybrid_retry = hybrid_search(
            query=enriched_question, top_k=50, materials=materials,
        )
        reranked_retry = rerank(
            query=question, results=hybrid_retry, top_k=10
        )
        answer = generate_answer(
            question=enriched_question, chunks=reranked_retry
        )
        verification = verify_answer(answer=answer, chunks=reranked_retry)

        if verification.verdict == "FAIL" and verification.severity == "major":
            # Corrective fallback: instead of a blunt "insufficient data"
            # message, generate a structured response that reports what the
            # corpus DOES cover, suggests reformulated questions, and points
            # to the most relevant source documents.
            logger.warning(
                "Verification FAILED again — generating graceful fallback"
            )
            answer = generate_fallback_answer(
                question=question,
                chunks=reranked_retry,
                verification_issues=verification.issues,
            )
            reranked = reranked_retry
            chunks_after_rerank = len(reranked)
            is_fallback = True

    # Build enriched response
    elapsed_ms = int((time.time() - start_time) * 1000)
    sources = _build_sources(reranked)
    graph_data = _extract_graph_data(graph_results)
    confidence = _compute_confidence(
        verification, chunks_after_rerank, retrieval_method
    )

    # Generate follow-up questions (non-blocking best-effort)
    follow_ups = _generate_follow_ups(
        question, answer, query_type.value
    )

    response = QueryResponse(
        answer=answer,
        sources=sources,
        verification=verification,
        follow_up_questions=follow_ups,
        graph_data=graph_data,
        metadata={
            "query_type": query_type.value,
            "retrieval_method": retrieval_method,
            "chunks_retrieved": chunks_retrieved,
            "chunks_after_rerank": chunks_after_rerank,
            "latency_ms": elapsed_ms,
            "confidence": round(confidence, 2),
            "is_fallback": is_fallback,
            "from_cache": False,
        },
    )

    logger.info(
        "Query complete: type=%s, chunks=%d→%d, verified=%s, "
        "confidence=%.2f, %dms",
        query_type.value, chunks_retrieved, chunks_after_rerank,
        verification.verdict, confidence, elapsed_ms,
    )

    # Cache write — skip fallback responses ("we don't have enough
    # data") so a future corpus update can fix them immediately
    # instead of waiting 24 hours for the cache to expire.
    if not is_fallback:
        set_cached_response(cache_key, question, response.model_dump())

    return response
