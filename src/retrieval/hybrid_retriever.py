"""Hybrid retrieval: vector + BM25 merged via Reciprocal Rank Fusion (RRF)."""

import logging

from src.config import settings
from src.retrieval.bm25_retriever import bm25_search
from src.retrieval.vector_retriever import RetrievalResult, vector_search

logger = logging.getLogger(__name__)

# Number of top BM25 results guaranteed to reach the reranker regardless of
# RRF score. Protects small docs (e.g., a 5-chunk DPA announcement) from being
# drowned out when large docs (500+ chunks) dominate both retrievers and win
# the RRF double-scoring contest.
BM25_GUARANTEED_FLOOR = 5


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
    bm25_floor: int = BM25_GUARANTEED_FLOOR,
) -> list[RetrievalResult]:
    """Run vector + BM25 search in parallel and merge via RRF.

    After RRF merging, guarantees that the top-N BM25 results always reach the
    reranker regardless of their RRF score. Without this, a doc that appears
    in only one retriever's list (typical for small docs with unique keywords)
    can be pushed below the top-K cutoff by docs that appear in both lists
    and win the RRF double-scoring.

    Args:
        query: The search query string.
        top_k: Number of final results to return.
        materials: Optional filter by materials.
        doc_type: Optional filter by document type.
        bm25_floor: Number of top BM25 matches guaranteed to be included.

    Returns:
        Merged results: top_k by RRF score, plus any BM25 top-N not already
        present. The reranker evaluates each candidate independently, so the
        extra items just expand the candidate pool it sees.
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

    # Take top-K from the RRF ranking
    final: list[RetrievalResult] = merged[:k]
    final_ids = {r.chunk_id for r in final}

    # Guarantee top-N BM25 matches are always in the candidate pool
    rescued = 0
    for bm25_result in bm25_results[:bm25_floor]:
        if bm25_result.chunk_id and bm25_result.chunk_id not in final_ids:
            rescued_result = bm25_result.model_copy()
            rescued_result.source = "hybrid"
            final.append(rescued_result)
            final_ids.add(bm25_result.chunk_id)
            rescued += 1

    logger.info(
        "Hybrid search: %d vector + %d BM25 → %d merged → %d final "
        "(%d BM25 rescued below RRF cutoff)",
        len(vector_results),
        len(bm25_results),
        len(merged),
        len(final),
        rescued,
    )
    return final
