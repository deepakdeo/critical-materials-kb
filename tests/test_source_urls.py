"""Tests for the source URL mapping module."""

from src.api.source_urls import SOURCE_URL_MAP, get_all_sources, get_source_url


class TestGetSourceUrl:
    """Tests for get_source_url function."""

    def test_known_document(self) -> None:
        url = get_source_url("mcs2025.pdf")
        assert url is not None
        assert "usgs.gov" in url

    def test_unknown_document_returns_none(self) -> None:
        assert get_source_url("nonexistent.pdf") is None

    def test_knowledge_graph_returns_none(self) -> None:
        assert get_source_url("Knowledge Graph") is None


class TestGetAllSources:
    """Tests for get_all_sources function."""

    def test_returns_list(self) -> None:
        sources = get_all_sources()
        assert isinstance(sources, list)
        assert len(sources) > 0

    def test_excludes_knowledge_graph(self) -> None:
        sources = get_all_sources()
        names = [s["name"] for s in sources]
        assert "Knowledge Graph" not in names

    def test_all_have_url(self) -> None:
        sources = get_all_sources()
        for source in sources:
            assert source["url"] is not None
            assert source["url"] != ""

    def test_each_entry_has_name_and_url(self) -> None:
        sources = get_all_sources()
        for source in sources:
            assert "name" in source
            assert "url" in source


class TestSourceUrlMapIntegrity:
    """Tests that the SOURCE_URL_MAP entries are well-formed."""

    def test_all_urls_are_https(self) -> None:
        for name, url in SOURCE_URL_MAP.items():
            if url is not None:
                assert url.startswith("https://"), f"{name} URL doesn't use HTTPS: {url}"

    def test_no_empty_urls(self) -> None:
        for name, url in SOURCE_URL_MAP.items():
            if url is not None:
                assert len(url) > 10, f"{name} has suspiciously short URL: {url}"

    def test_expected_source_count(self) -> None:
        # We have 26 real documents + Knowledge Graph (None)
        real_sources = [k for k, v in SOURCE_URL_MAP.items() if v is not None]
        assert len(real_sources) == 26

    def test_key_documents_present(self) -> None:
        """Verify critical documents are in the map."""
        expected_keys = [
            "mcs2025.pdf",
            "mcs2026.pdf",
            "gao-24-107176.pdf",
            "R47833.2.pdf",
        ]
        for key in expected_keys:
            assert key in SOURCE_URL_MAP, f"Missing expected document: {key}"
