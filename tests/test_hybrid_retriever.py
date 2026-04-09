"""Tests for the hybrid retriever's RRF merge, BM25 rescue, and title boost."""

from unittest.mock import patch

import pytest

from src.retrieval.hybrid_retriever import (
    BM25_GUARANTEED_FLOOR,
    _build_doc_title_index,
    _doc_title_boost,
    _extract_tokens,
    hybrid_search,
    reciprocal_rank_fusion,
)
from src.retrieval.vector_retriever import RetrievalResult


@pytest.fixture(autouse=True)
def _clear_doc_title_cache():
    """Each test starts with a clean doc-title index cache."""
    _build_doc_title_index.cache_clear()
    yield
    _build_doc_title_index.cache_clear()


@pytest.fixture(autouse=True)
def _stub_doc_title_boost():
    """Default to a no-op title boost so RRF/rescue tests don't hit Supabase.

    Tests that specifically exercise the boost path patch list_documents
    + get_chunks_by_document_id directly and can do so inside their own
    patch contexts (this autouse stub still covers the default path).
    """
    with patch(
        "src.retrieval.hybrid_retriever._doc_title_boost", return_value=[]
    ):
        yield


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


class TestExtractTokens:
    def test_drops_short_tokens(self) -> None:
        # 3-char tokens like "the", "iii", "and" are below the length floor
        assert _extract_tokens("the III tungsten") == {"tungsten"}

    def test_drops_generic_tokens(self) -> None:
        # "html" is in the generic boilerplate set
        assert "html" not in _extract_tokens("dpa-fireweed-mactung.html")

    def test_drops_source_acronyms(self) -> None:
        # "doe", "gao", "dpa" don't disambiguate between corpus docs
        tokens = _extract_tokens("doe gao dpa report on tungsten")
        assert "doe" not in tokens
        assert "gao" not in tokens
        assert "dpa" not in tokens
        assert "tungsten" in tokens

    def test_keeps_distinctive_words(self) -> None:
        tokens = _extract_tokens("Fireweed Metals MacTung project")
        assert "fireweed" in tokens
        assert "mactung" in tokens
        assert "metals" in tokens

    def test_lowercases(self) -> None:
        assert _extract_tokens("FIREWEED") == {"fireweed"}


class TestDocTitleBoost:
    """The fix that routes named-entity queries to the right small doc."""

    @staticmethod
    def _fake_docs() -> list[dict]:
        return [
            {"id": "doc-fireweed", "name": "dpa-fireweed-mactung-2024.html"},
            {"id": "doc-battery", "name": "dpa-battery-minerals-2022.html"},
            {"id": "doc-doe-battery", "name": "doe-battery-supply-chain-review-2024.pdf"},
            {"id": "doc-mcs", "name": "mcs2025.pdf"},  # no alpha tokens
            {"id": "doc-kennametal", "name": "kennametal-tungsten-powders.html"},
        ]

    @staticmethod
    def _fake_chunk(doc_id: str, idx: int) -> dict:
        return {
            "id": f"{doc_id}-chunk-{idx}",
            "document_id": doc_id,
            "text": f"text from {doc_id}",
            "section_title": "",
            "page_numbers": [],
            "materials": [],
            "metadata": {},
        }

    def test_query_with_distinctive_tokens_routes_to_right_doc(self) -> None:
        """'Fireweed MacTung' must surface the dpa-fireweed-mactung doc."""
        with (
            patch(
                "src.retrieval.hybrid_retriever.list_documents",
                return_value=self._fake_docs(),
            ),
            patch(
                "src.retrieval.hybrid_retriever.get_chunks_by_document_id"
            ) as mock_get,
        ):
            mock_get.side_effect = lambda doc_id, limit: [
                self._fake_chunk(doc_id, i) for i in range(limit)
            ]
            results = _doc_title_boost(
                "Which materials does Fireweed Metals' MacTung project produce?",
                max_docs=3,
                chunks_per_doc=2,
            )

        result_doc_ids = {r.document_id for r in results}
        assert "doc-fireweed" in result_doc_ids
        # MCS has no alpha tokens, must NOT be matched
        assert "doc-mcs" not in result_doc_ids

    def test_multi_token_overlap_outranks_single_token(self) -> None:
        """'battery minerals' (2 tokens in dpa-battery-minerals) wins over
        the doe-battery doc (only 1 token overlap)."""
        captured_doc_ids: list[str] = []

        def fake_get(doc_id, limit):
            captured_doc_ids.append(doc_id)
            return [self._fake_chunk(doc_id, 0)]

        with (
            patch(
                "src.retrieval.hybrid_retriever.list_documents",
                return_value=self._fake_docs(),
            ),
            patch(
                "src.retrieval.hybrid_retriever.get_chunks_by_document_id",
                side_effect=fake_get,
            ),
        ):
            _doc_title_boost(
                "Which DPA Title III awards for critical battery minerals?",
                max_docs=2,
            )

        # The 2-overlap doc must come first (we sort by overlap desc)
        assert captured_doc_ids[0] == "doc-battery"

    def test_no_overlap_returns_empty(self) -> None:
        with (
            patch(
                "src.retrieval.hybrid_retriever.list_documents",
                return_value=self._fake_docs(),
            ),
            patch(
                "src.retrieval.hybrid_retriever.get_chunks_by_document_id",
                return_value=[],
            ),
        ):
            results = _doc_title_boost("What is the weather today?")
        assert results == []

    def test_max_docs_caps_pool_growth(self) -> None:
        """max_docs prevents an over-broad query from injecting many docs."""
        with (
            patch(
                "src.retrieval.hybrid_retriever.list_documents",
                return_value=self._fake_docs(),
            ),
            patch(
                "src.retrieval.hybrid_retriever.get_chunks_by_document_id"
            ) as mock_get,
        ):
            mock_get.return_value = [{
                "id": "x", "document_id": "y", "text": "",
                "section_title": "", "page_numbers": [], "materials": [],
                "metadata": {},
            }]
            # query that touches many docs ("battery" hits 2, "tungsten" hits 1)
            _doc_title_boost(
                "battery minerals tungsten powders fireweed mactung",
                max_docs=2,
            )
        assert mock_get.call_count == 2

    def test_index_handles_list_documents_failure(self) -> None:
        """A Supabase outage during cache build returns empty, doesn't crash."""
        with patch(
            "src.retrieval.hybrid_retriever.list_documents",
            side_effect=RuntimeError("supabase down"),
        ):
            results = _doc_title_boost("anything")
        assert results == []
