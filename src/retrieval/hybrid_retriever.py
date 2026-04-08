"""Hybrid retrieval: vector + BM25 merged via Reciprocal Rank Fusion (RRF)."""

import logging

from src.config import settings
from src.retrieval.bm25_retriever import bm25_search
from src.retrieval.vector_retriever import RetrievalResult, vector_search

logger = logging.getLogger(__name__)


def reciprocal_rank_fusion(
    result_lists: list[list[RetrievalResult]],
    k: int | None = None,
) -> list[RetrievalResult]:
    """Merge multiple ranked result lists using Reciprocal Rank Fusion.

    RRF_score(doc) = sum(1 / (k + rank_in_list)) for each list the doc appears in.
    Documents appearing in multiple lists get boosted.

    Args:
        result_lists: List of ranked result lists to merge.
        k: RRF constant (default: settings.rrf_k = 60).

    Returns:
        Merged and re-scored results sorted by RRF score descending.
    """
    rrf_k = k or settings.rrf_k
    scores: dict[str, float] = {}
    result_map: dict[str, RetrievalResult] = {}

    for result_list in result_lists:
        for rank, result in enumerate(result_list, start=1):
            key = result.chunk_id
            if key not in result_map:
                result_map[key] = result
            scores[key] = scores.get(key, 0.0) + 1.0 / (rrf_k + rank)

    # Sort by RRF score
    sorted_keys = sorted(scores.keys(), key=lambda cid: scores[cid], reverse=True)

    merged = []
    for key in sorted_keys:
        result = result_map[key].model_copy()
        result.score = scores[key]
        result.source = "hybrid"
        merged.append(result)

    return merged


def hybrid_search(
    query: str,
    top_k: int | None = None,
    materials: list[str] | None = None,
    doc_type: str | None = None,
) -> list[RetrievalResult]:
    """Run vector + BM25 search in parallel and merge via RRF.

    Args:
        query: The search query string.
        top_k: Number of final results to return.
        materials: Optional filter by materials.
        doc_type: Optional filter by document type.

    Returns:
        Merged results sorted by RRF score, limited to top_k.
    """
    k = top_k or settings.retrieval_top_k

    # Run both retrievers (each fetches retrieval_top_k candidates)
    vector_results = vector_search(
        query=query, top_k=k, materials=materials, doc_type=doc_type
    )
    bm25_results = bm25_search(
        query=query, top_k=k, materials=materials, doc_type=doc_type
    )

    # Merge via RRF
    merged = reciprocal_rank_fusion([vector_results, bm25_results])

    logger.info(
        "Hybrid search: %d vector + %d BM25 → %d merged (returning top %d)",
        len(vector_results),
        len(bm25_results),
        len(merged),
        k,
    )
    return merged[:k]
