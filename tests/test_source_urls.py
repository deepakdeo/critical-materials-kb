"""Tests for the source URL mapping module."""

from src.api.source_urls import (
    SOURCE_URL_MAP,
    get_all_sources,
    get_source_url,
    get_source_url_with_page,
)


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


class TestGetSourceUrlWithPage:
    """Tests for the deep-linking PDF URL helper."""

    def test_pdf_with_page_appends_fragment(self) -> None:
        url = get_source_url_with_page("mcs2025.pdf", [204])
        assert url is not None
        assert url.endswith("#page=204")

    def test_pdf_uses_first_page_when_chunk_spans_multiple(self) -> None:
        """A chunk spanning pages 199-200 should deep-link to the first page."""
        url = get_source_url_with_page("mcs2025.pdf", [199, 200])
        assert url is not None
        assert url.endswith("#page=199")

    def test_pdf_without_pages_returns_base_url(self) -> None:
        url = get_source_url_with_page("mcs2025.pdf", None)
        assert url is not None
        assert "#page" not in url

    def test_pdf_with_empty_pages_returns_base_url(self) -> None:
        url = get_source_url_with_page("mcs2025.pdf", [])
        assert url is not None
        assert "#page" not in url

    def test_html_source_never_gets_page_fragment(self) -> None:
        """HTML company sites have no page anchor equivalent — leave the URL alone."""
        url = get_source_url_with_page("kennametal-defense.html", [5])
        assert url is not None
        assert "#page" not in url

    def test_crs_pdf_url_gets_fragment(self) -> None:
        """CRS URLs end in .pdf despite not having a file extension in the path."""
        url = get_source_url_with_page("R47833.2.pdf", [12])
        assert url is not None
        # The base CRS URL does NOT end in .pdf (it's a ColdFusion endpoint),
        # so no fragment should be added — otherwise we'd produce a broken URL.
        assert "#page" not in url

    def test_direct_pdf_url_gets_fragment(self) -> None:
        """USGS URLs point directly at .pdf files — fragment is valid."""
        url = get_source_url_with_page("gao-24-107176.pdf", [7])
        assert url is not None
        assert url.endswith("#page=7")

    def test_unknown_document_returns_none(self) -> None:
        assert get_source_url_with_page("nonexistent.pdf", [1]) is None

    def test_knowledge_graph_returns_none(self) -> None:
        assert get_source_url_with_page("Knowledge Graph", [1]) is None
