"""Tests for the graph retriever entity extraction and formatting."""

from src.retrieval.graph_retriever import _extract_entities, _format_graph_results


class TestExtractEntities:
    """Tests for entity extraction from query strings."""

    def test_extracts_single_material(self) -> None:
        result = _extract_entities("Who produces tungsten?")
        assert "tungsten" in result["materials"]

    def test_extracts_multiple_materials(self) -> None:
        result = _extract_entities("Compare tungsten and cobalt supply chains")
        assert "tungsten" in result["materials"]
        assert "cobalt" in result["materials"]

    def test_extracts_country(self) -> None:
        result = _extract_entities("What if China cuts tungsten exports?")
        assert "china" in result["countries"]
        assert "tungsten" in result["materials"]

    def test_extracts_multiple_countries(self) -> None:
        result = _extract_entities("Compare China and Australia rare earth production")
        assert "china" in result["countries"]
        assert "australia" in result["countries"]

    def test_no_entities_found(self) -> None:
        result = _extract_entities("What is the weather today?")
        assert result["materials"] == []
        assert result["countries"] == []

    def test_case_insensitive(self) -> None:
        result = _extract_entities("TUNGSTEN supply from CHINA")
        assert "tungsten" in result["materials"]
        assert "china" in result["countries"]

    def test_rare_earth_as_material(self) -> None:
        result = _extract_entities("Rare earth elements supply chain")
        assert "rare earth" in result["materials"]

    def test_united_states_as_country(self) -> None:
        result = _extract_entities("United States cobalt imports")
        assert "united states" in result["countries"]


class TestFormatGraphResults:
    """Tests for formatting graph query results."""

    def test_empty_results(self) -> None:
        assert _format_graph_results([], "test") == ""

    def test_single_result(self) -> None:
        results = [{"company": "Kennametal", "role": "PRODUCES", "material": "Tungsten"}]
        formatted = _format_graph_results(results, "suppliers of tungsten")
        assert "Graph Knowledge" in formatted
        assert "Kennametal" in formatted
        assert "Tungsten" in formatted

    def test_skips_none_values(self) -> None:
        results = [{"company": "Kennametal", "role": "PRODUCES", "extra": None}]
        formatted = _format_graph_results(results, "test")
        assert "None" not in formatted

    def test_skips_empty_lists(self) -> None:
        results = [{"company": "Kennametal", "tags": []}]
        formatted = _format_graph_results(results, "test")
        assert "[]" not in formatted

    def test_multiple_results(self) -> None:
        results = [
            {"company": "Kennametal", "material": "Tungsten"},
            {"company": "GTP", "material": "Tungsten"},
        ]
        formatted = _format_graph_results(results, "suppliers")
        assert "Kennametal" in formatted
        assert "GTP" in formatted
