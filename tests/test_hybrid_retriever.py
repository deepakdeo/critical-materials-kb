"""Tests for the hybrid retriever's RRF merge and BM25 rescue behavior."""

from unittest.mock import patch

from src.retrieval.hybrid_retriever import (
    BM25_GUARANTEED_FLOOR,
    hybrid_search,
    reciprocal_rank_fusion,
)
from src.retrieval.vector_retriever import RetrievalResult


def _mk(chunk_id: str, source: str = "vector", score: float = 0.5) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=chunk_id,
        document_id=f"doc-{chunk_id}",
        text=f"text for {chunk_id}",
        score=score,
        source=source,
    )


class TestReciprocalRankFusion:
    def test_doc_in_both_lists_outranks_singletons(self) -> None:
        """A doc appearing in both retrievers beats any pure singleton."""
        vec = [_mk("A"), _mk("B"), _mk("C")]
        bm = [_mk("B", "bm25"), _mk("D", "bm25"), _mk("E", "bm25")]
        merged = reciprocal_rank_fusion([vec, bm])
        # B appears in both lists, should rank first
        assert merged[0].chunk_id == "B"
        assert merged[0].source == "hybrid"

    def test_preserves_all_unique_docs(self) -> None:
        vec = [_mk("A"), _mk("B")]
        bm = [_mk("C", "bm25"), _mk("D", "bm25")]
        merged = reciprocal_rank_fusion([vec, bm])
        assert {r.chunk_id for r in merged} == {"A", "B", "C", "D"}


class TestHybridSearchBm25Floor:
    """The critical fix: guarantee BM25 top-N reaches the reranker."""

    def test_bm25_top_match_rescued_below_rrf_cutoff(self) -> None:
        """BM25 rank-1 gets rescued even when RRF ranks it out of top_k.

        Simulates the real-world bug: MCS has 500+ chunks that both retrievers
        love, pushing a 5-chunk DPA announcement doc below the top_k cutoff.
        The BM25 rank-1 match (the DPA doc) must still reach the reranker.
        """
        # Vector and BM25 agree on 30 "mcs" chunks at the top — these all
        # double-score under RRF and dominate
        vec = [_mk(f"mcs-{i}") for i in range(30)]
        bm = [_mk(f"mcs-{i}", "bm25") for i in range(30)]
        # But BM25 also has a very rare exact-match chunk at rank 1 that
        # the vector retriever didn't find
        bm[0] = _mk("rare-dpa-doc", "bm25")

        with (
            patch("src.retrieval.hybrid_retriever.vector_search", return_value=vec),
            patch("src.retrieval.hybrid_retriever.bm25_search", return_value=bm),
        ):
            results = hybrid_search("Fireweed MacTung", top_k=20)

        ids = [r.chunk_id for r in results]
        assert "rare-dpa-doc" in ids, (
            "BM25 rank-1 exact match should be rescued into candidate pool"
        )

    def test_rescue_only_adds_missing_items(self) -> None:
        """BM25 rank-1 already in top-K shouldn't be duplicated."""
        shared = [_mk(f"shared-{i}") for i in range(10)]
        vec = shared[:]
        bm = [_mk(f"shared-{i}", "bm25") for i in range(10)]

        with (
            patch("src.retrieval.hybrid_retriever.vector_search", return_value=vec),
            patch("src.retrieval.hybrid_retriever.bm25_search", return_value=bm),
        ):
            results = hybrid_search("q", top_k=10)

        ids = [r.chunk_id for r in results]
        # No duplicates
        assert len(ids) == len(set(ids))

    def test_rescue_respects_bm25_floor_parameter(self) -> None:
        """Only the first N BM25 results are rescued, not all of them."""
        # 20 shared docs that overlap in vec+bm25 and win RRF, plus 10
        # unique BM25-only docs. With top_k=20 the overlap docs fill all
        # 20 slots and every bm-only-* is below the RRF cutoff.
        shared_vec = [_mk(f"shared-{i}") for i in range(20)]
        shared_bm = [_mk(f"shared-{i}", "bm25") for i in range(20)]
        # Interleave 3 unique BM25 results at the top of BM25
        bm = [
            _mk("bm-unique-0", "bm25"),
            _mk("bm-unique-1", "bm25"),
            _mk("bm-unique-2", "bm25"),
            _mk("bm-unique-3", "bm25"),
            *shared_bm,
        ]

        with (
            patch(
                "src.retrieval.hybrid_retriever.vector_search",
                return_value=shared_vec,
            ),
            patch("src.retrieval.hybrid_retriever.bm25_search", return_value=bm),
        ):
            results = hybrid_search("q", top_k=20, bm25_floor=3)

        ids = {r.chunk_id for r in results}
        # First 3 unique BM25 must be rescued
        assert {"bm-unique-0", "bm-unique-1", "bm-unique-2"} <= ids
        # The 4th BM25 unique (beyond floor) must NOT be rescued
        assert "bm-unique-3" not in ids

    def test_default_floor_constant_is_reasonable(self) -> None:
        """Sanity check: the default floor is a small positive integer."""
        assert 1 <= BM25_GUARANTEED_FLOOR <= 10
