"""Hybrid retrieval: vector + BM25 merged via Reciprocal Rank Fusion (RRF)."""

import logging
import re
from functools import lru_cache

from src.config import settings
from src.retrieval.bm25_retriever import bm25_search
from src.retrieval.vector_retriever import RetrievalResult, vector_search
from src.store.metadata_store import list_documents
from src.store.vector_store import get_chunks_by_document_id

logger = logging.getLogger(__name__)

# Number of top BM25 results guaranteed to reach the reranker regardless of
# RRF score. Protects small docs (e.g., a 5-chunk DPA announcement) from being
# drowned out when large docs (500+ chunks) dominate both retrievers and win
# the RRF double-scoring contest.
BM25_GUARANTEED_FLOOR = 5

# Doc-title boost: match query tokens against tokens extracted from document
# filenames. Helps named-entity queries reach the right small doc when BM25
# tokenization misses on phrases ("Fireweed MacTung", "battery minerals").
_TOKEN_RE = re.compile(r"[a-zA-Z]{4,}")

# Tokens that appear in doc filenames but don't disambiguate between docs
# (corpus boilerplate, common acronyms, generic words). These get filtered
# from both query tokenization and doc-name tokenization.
_GENERIC_TOKENS: frozenset[str] = frozenset({
    # File extensions and document boilerplate
    "html", "pdf", "report", "final", "rule", "page",
    "about", "overview", "brief", "fact", "sheet",
    # Source-organization acronyms (appear in many doc names)
    "doe", "gao", "usgs", "ncsc", "dpa", "dfars", "ndaa", "crs",
    # Common English query/connector words that survive the length filter
    "which", "what", "where", "when", "have", "been", "made", "from",
    "with", "this", "that", "they", "them", "their", "would", "could",
    "should", "does", "into", "than", "then", "such", "some", "more",
    "most", "many", "much", "also", "only", "very", "much",
})

# Per-doc title-token cache: document_id -> set of distinctive tokens.
# Built lazily on first call from list_documents().


def _extract_tokens(text: str) -> set[str]:
    """Extract content-bearing tokens from a string (query or filename)."""
    return {
        t for t in _TOKEN_RE.findall(text.lower())
        if t not in _GENERIC_TOKENS
    }


@lru_cache(maxsize=1)
def _build_doc_title_index() -> list[tuple[str, frozenset[str]]]:
    """Build a list of (document_id, title_tokens) for all corpus docs.

    Cached for the process lifetime: the document set doesn't change between
    queries in a running API process. Tests can clear the cache by calling
    _build_doc_title_index.cache_clear().
    """
    try:
        docs = list_documents(limit=500)
    except Exception as e:
        logger.warning("Doc title index build failed: %s", e)
        return []

    index: list[tuple[str, frozenset[str]]] = []
    for doc in docs:
        doc_id = doc.get("id", "")
        name = doc.get("name", "")
        if not doc_id or not name:
            continue
        tokens = _extract_tokens(name)
        if tokens:
            index.append((doc_id, frozenset(tokens)))
    return index


def _doc_title_boost(
    query: str,
    max_docs: int = 3,
    chunks_per_doc: int = 4,
) -> list[RetrievalResult]:
    """Surface chunks from docs whose filename overlaps with query tokens.

    Scores each doc by how many distinctive tokens its filename shares with
    the query, then fetches a few chunks from the top-scoring docs and
    returns them for inclusion in the rerank candidate pool. The reranker
    decides whether they actually beat the existing candidates.

    Args:
        query: The user's query string.
        max_docs: Hard cap on docs to inject (avoids ballooning the pool).
        chunks_per_doc: How many leading chunks to pull per matched doc.

    Returns:
        RetrievalResult list (possibly empty). Score is set to the overlap
        count so the rerank pool can debug-display the boost source.
    """
    query_tokens = _extract_tokens(query)
    if not query_tokens:
        return []

    index = _build_doc_title_index()
    if not index:
        return []

    # Score docs by token overlap
    scored: list[tuple[int, str]] = []
    for doc_id, doc_tokens in index:
        overlap = len(query_tokens & doc_tokens)
        if overlap > 0:
            scored.append((overlap, doc_id))

    if not scored:
        return []

    # Highest-overlap docs first, take top max_docs
    scored.sort(reverse=True)
    top_docs = scored[:max_docs]

    results: list[RetrievalResult] = []
    for overlap, doc_id in top_docs:
        try:
            rows = get_chunks_by_document_id(doc_id, limit=chunks_per_doc)
        except Exception as e:
            logger.warning(
                "Doc title boost: chunk fetch failed for %s: %s", doc_id, e
            )
            continue
        for row in rows:
            results.append(RetrievalResult(
                chunk_id=str(row.get("id", "")),
                document_id=str(row.get("document_id", "")),
                text=row.get("text", ""),
                section_title=row.get("section_title", ""),
                page_numbers=row.get("page_numbers", []),
                materials=row.get("materials", []),
                metadata=row.get("metadata", {}),
                score=float(overlap),
                source="title_boost",
            ))

    if results:
        logger.info(
            "Doc title boost: %d doc(s) matched, %d chunk(s) added",
            len(top_docs), len(results),
        )
    return results


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

    # Doc-title boost: if the query mentions tokens from a doc filename
    # (e.g., "Fireweed MacTung" → dpa-fireweed-mactung-2024.html), seed the
    # candidate pool with chunks from those docs. The reranker decides
    # whether they actually win against the existing candidates.
    boosted = 0
    for boost_result in _doc_title_boost(query):
        if boost_result.chunk_id and boost_result.chunk_id not in final_ids:
            final.append(boost_result)
            final_ids.add(boost_result.chunk_id)
            boosted += 1

    logger.info(
        "Hybrid search: %d vector + %d BM25 → %d merged → %d final "
        "(%d BM25 rescued, %d title-boosted)",
        len(vector_results),
        len(bm25_results),
        len(merged),
        len(final),
        rescued,
        boosted,
    )
    return final
