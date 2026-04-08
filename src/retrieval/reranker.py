"""Cross-encoder reranking using sentence-transformers."""

import logging

from sentence_transformers import CrossEncoder

from src.config import settings
from src.retrieval.vector_retriever import RetrievalResult

logger = logging.getLogger(__name__)

_model: CrossEncoder | None = None


def _get_model() -> CrossEncoder:
    """Load the cross-encoder model (cached after first call)."""
    global _model
    if _model is None:
        logger.info("Loading cross-encoder model: %s", settings.reranker_model)
        _model = CrossEncoder(settings.reranker_model)
        logger.info("Cross-encoder model loaded.")
    return _model


def rerank(
    query: str,
    results: list[RetrievalResult],
    top_k: int | None = None,
) -> list[RetrievalResult]:
    """Rerank retrieval results using a cross-encoder model.

    Passes each (query, chunk_text) pair through the cross-encoder for
    full bidirectional attention scoring, which is more accurate than
    the initial retrieval scores.

    Args:
        query: The original search query.
        results: Candidate results from hybrid retrieval.
        top_k: Number of top results to return after reranking.

    Returns:
        Top-k results re-scored and sorted by cross-encoder relevance.
    """
    k = top_k or settings.rerank_top_k

    if not results:
        return []

    if len(results) <= k:
        return results

    model = _get_model()

    # Create (query, text) pairs for the cross-encoder
    pairs = [[query, r.text] for r in results]

    # Score all pairs
    scores = model.predict(pairs)

    # Attach scores and sort
    scored_results = []
    for result, score in zip(results, scores):
        reranked = result.model_copy()
        reranked.score = float(score)
        scored_results.append(reranked)

    scored_results.sort(key=lambda r: r.score, reverse=True)

    logger.info(
        "Reranked %d candidates → top %d (scores: %.3f to %.3f)",
        len(results),
        k,
        scored_results[0].score if scored_results else 0,
        scored_results[min(k, len(scored_results)) - 1].score if scored_results else 0,
    )
    return scored_results[:k]
