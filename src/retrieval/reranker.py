"""Reranking via the Cohere Rerank API.

Uses Cohere's hosted rerank endpoint instead of a local cross-encoder so
deployments don't need to ship PyTorch / CUDA wheels. A free Cohere trial
key (https://dashboard.cohere.com/api-keys) is sufficient for demo use.
"""

import logging

import cohere

from src.config import settings
from src.retrieval.vector_retriever import RetrievalResult

logger = logging.getLogger(__name__)

_client: cohere.Client | None = None


def _get_client() -> cohere.Client:
    """Return a cached Cohere client."""
    global _client
    if _client is None:
        if not settings.cohere_api_key:
            raise RuntimeError(
                "COHERE_API_KEY is not set. Get a free key at "
                "https://dashboard.cohere.com/api-keys"
            )
        _client = cohere.Client(settings.cohere_api_key)
        logger.info("Initialized Cohere client for reranking.")
    return _client


def rerank(
    query: str,
    results: list[RetrievalResult],
    top_k: int | None = None,
) -> list[RetrievalResult]:
    """Rerank retrieval results using the Cohere Rerank API.

    Args:
        query: The original search query.
        results: Candidate results from hybrid retrieval.
        top_k: Number of top results to return after reranking.

    Returns:
        Top-k results re-scored and sorted by Cohere relevance score.
    """
    k = top_k or settings.rerank_top_k

    if not results:
        return []

    if len(results) <= k:
        return results

    client = _get_client()
    documents = [r.text for r in results]

    response = client.rerank(
        query=query,
        documents=documents,
        top_n=k,
        model=settings.reranker_model,
    )

    scored_results: list[RetrievalResult] = []
    for item in response.results:
        original = results[item.index]
        reranked = original.model_copy()
        reranked.score = float(item.relevance_score)
        scored_results.append(reranked)

    logger.info(
        "Reranked %d candidates → top %d (scores: %.3f to %.3f)",
        len(results),
        k,
        scored_results[0].score if scored_results else 0,
        scored_results[-1].score if scored_results else 0,
    )
    return scored_results
