"""Tests for the chains module — source building, graph data extraction, confidence."""

from src.generation.chains import (
    _build_sources,
    _compute_confidence,
    _extract_graph_data,
)
from src.generation.verifier import VerificationResult
from src.retrieval.vector_retriever import RetrievalResult


def _make_chunk(
    source_name: str = "test.pdf",
    pages: list[int] | None = None,
    section: str = "",
    score: float = 0.8,
    text: str = "Sample chunk text.",
) -> RetrievalResult:
    """Helper to create a RetrievalResult for testing."""
    return RetrievalResult(
        text=text,
        score=score,
        page_numbers=pages or [],
        section_title=section,
        metadata={
            "source_name": source_name,
            "document_type": "usgs_mcs",
        },
    )


class TestBuildSources:
    """Tests for _build_sources."""

    def test_basic_source_extraction(self) -> None:
        chunks = [_make_chunk(source_name="mcs2025.pdf", pages=[5, 6], section="Tungsten")]
        sources = _build_sources(chunks)
        assert len(sources) == 1
        assert sources[0].name == "mcs2025.pdf"
        assert "5" in sources[0].page
        assert sources[0].section == "Tungsten"

    def test_deduplicates_same_source_and_page(self) -> None:
        chunks = [
            _make_chunk(source_name="mcs2025.pdf", pages=[5]),
            _make_chunk(source_name="mcs2025.pdf", pages=[5]),
        ]
        sources = _build_sources(chunks)
        assert len(sources) == 1

    def test_different_pages_not_deduplicated(self) -> None:
        chunks = [
            _make_chunk(source_name="mcs2025.pdf", pages=[5]),
            _make_chunk(source_name="mcs2025.pdf", pages=[10]),
        ]
        sources = _build_sources(chunks)
        assert len(sources) == 2

    def test_empty_page_numbers(self) -> None:
        chunks = [_make_chunk(source_name="Knowledge Graph", pages=[])]
        sources = _build_sources(chunks)
        assert len(sources) == 1
        assert sources[0].page == ""

    def test_source_url_lookup(self) -> None:
        chunks = [_make_chunk(source_name="mcs2025.pdf", pages=[1])]
        sources = _build_sources(chunks)
        assert sources[0].source_url is not None
        assert "usgs.gov" in sources[0].source_url

    def test_chunk_text_truncated(self) -> None:
        long_text = "x" * 1000
        chunks = [_make_chunk(text=long_text)]
        sources = _build_sources(chunks)
        assert len(sources[0].chunk_text) <= 500


class TestExtractGraphData:
    """Tests for _extract_graph_data and edge deduplication."""

    def _make_graph_result(self, text: str) -> RetrievalResult:
        return RetrievalResult(
            text=text,
            score=0.8,
            page_numbers=[],
            section_title="Knowledge Graph",
            metadata={"source_name": "Knowledge Graph", "document_type": "graph"},
        )

    def test_empty_results(self) -> None:
        result = _extract_graph_data([])
        assert result == {"nodes": [], "edges": []}

    def test_parses_company_material(self) -> None:
        text = "  - company: Kennametal | role: PRODUCES | material: Tungsten"
        result = _extract_graph_data([self._make_graph_result(text)])
        assert len(result["nodes"]) == 2
        assert len(result["edges"]) == 1
        node_labels = {n["label"] for n in result["nodes"]}
        assert "Kennametal" in node_labels
        assert "Tungsten" in node_labels

    def test_parses_country_material(self) -> None:
        text = "  - country: China | role: PRODUCES | material: Tungsten"
        result = _extract_graph_data([self._make_graph_result(text)])
        node_types = {n["type"] for n in result["nodes"]}
        assert "Country" in node_types
        assert "Material" in node_types

    def test_parses_weapon_system(self) -> None:
        text = "  - weapon_system: F-35 | material: Tungsten"
        result = _extract_graph_data([self._make_graph_result(text)])
        node_types = {n["type"] for n in result["nodes"]}
        assert "WeaponSystem" in node_types

    def test_edge_deduplication(self) -> None:
        # Same relationship appears in multiple results
        text = "  - company: Kennametal | role: PRODUCES | material: Tungsten"
        results = [self._make_graph_result(text), self._make_graph_result(text)]
        result = _extract_graph_data(results)
        assert len(result["edges"]) == 1  # Deduplicated

    def test_different_edges_not_deduplicated(self) -> None:
        text1 = "  - company: Kennametal | role: PRODUCES | material: Tungsten"
        text2 = "  - company: GTP | role: PRODUCES | material: Tungsten"
        results = [self._make_graph_result(text1), self._make_graph_result(text2)]
        result = _extract_graph_data(results)
        assert len(result["edges"]) == 2

    def test_skips_none_values(self) -> None:
        text = "  - company: None | role: PRODUCES | material: Tungsten"
        result = _extract_graph_data([self._make_graph_result(text)])
        node_labels = {n["label"] for n in result["nodes"]}
        assert "None" not in node_labels

    def test_regulation_parsing(self) -> None:
        text = "  - regulation: DFARS 225.7018 | material: Tungsten"
        result = _extract_graph_data([self._make_graph_result(text)])
        node_types = {n["type"] for n in result["nodes"]}
        assert "Regulation" in node_types


class TestComputeConfidence:
    """Tests for confidence score computation."""

    def test_pass_verdict_high_confidence(self) -> None:
        v = VerificationResult(verdict="PASS", severity="none", issues=[])
        score = _compute_confidence(v, chunks_after_rerank=6, retrieval_method="hybrid+graph")
        assert score >= 0.9

    def test_fail_verdict_low_confidence(self) -> None:
        v = VerificationResult(
            verdict="FAIL", severity="major", issues=["Unsupported claim"]
        )
        score = _compute_confidence(v, chunks_after_rerank=2, retrieval_method="hybrid")
        assert score <= 0.6

    def test_graph_enrichment_bonus(self) -> None:
        v = VerificationResult(verdict="PASS", severity="none", issues=[])
        score_no_graph = _compute_confidence(v, 4, "hybrid")
        score_graph = _compute_confidence(v, 4, "hybrid+graph")
        assert score_graph > score_no_graph

    def test_more_chunks_higher_confidence(self) -> None:
        v = VerificationResult(verdict="PASS", severity="none", issues=[])
        score_few = _compute_confidence(v, 2, "hybrid")
        score_many = _compute_confidence(v, 8, "hybrid")
        assert score_many >= score_few

    def test_capped_at_one(self) -> None:
        v = VerificationResult(verdict="PASS", severity="none", issues=[])
        score = _compute_confidence(v, 10, "hybrid+graph")
        assert score <= 1.0
