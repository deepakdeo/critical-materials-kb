"""Tests for the document loader module."""

from pathlib import Path

import pytest

from src.ingest.loader import LoadedDocument, load_document


@pytest.fixture()
def sample_txt_file(tmp_path: Path) -> Path:
    """Create a sample text file for testing."""
    f = tmp_path / "sample.txt"
    f.write_text("This is a test document.\nIt has two lines.")
    return f


@pytest.fixture()
def sample_html_file(tmp_path: Path) -> Path:
    """Create a sample HTML file for testing."""
    f = tmp_path / "sample.html"
    f.write_text(
        "<html><head><title>Test</title></head>"
        "<body><h1>Heading</h1><p>Paragraph text here.</p></body></html>"
    )
    return f


@pytest.fixture()
def sample_pdf_file(tmp_path: Path) -> Path:
    """Create a minimal PDF file for testing.

    Uses a bare-minimum valid PDF structure with a single page containing text.
    """
    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R"
        b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
        b"4 0 obj<</Length 44>>stream\n"
        b"BT /F1 12 Tf 100 700 Td (Hello World) Tj ET\n"
        b"endstream endobj\n"
        b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
        b"xref\n0 6\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000266 00000 n \n"
        b"0000000360 00000 n \n"
        b"trailer<</Size 6/Root 1 0 R>>\n"
        b"startxref\n431\n%%EOF\n"
    )
    f = tmp_path / "sample.pdf"
    f.write_bytes(pdf_content)
    return f


class TestLoadText:
    """Tests for plain text loading."""

    def test_load_text_returns_loaded_document(self, sample_txt_file: Path) -> None:
        doc = load_document(sample_txt_file)
        assert isinstance(doc, LoadedDocument)
        assert doc.file_name == "sample.txt"
        assert "test document" in doc.text
        assert len(doc.pages) == 1
        assert doc.pages[0].page_number == 1

    def test_load_text_metadata(self, sample_txt_file: Path) -> None:
        doc = load_document(sample_txt_file)
        assert doc.metadata["format"] == "txt"


class TestLoadHTML:
    """Tests for HTML loading."""

    def test_load_html_extracts_body_text(self, sample_html_file: Path) -> None:
        doc = load_document(sample_html_file)
        assert isinstance(doc, LoadedDocument)
        assert "Heading" in doc.text
        assert "Paragraph text here." in doc.text

    def test_load_html_strips_tags(self, sample_html_file: Path) -> None:
        doc = load_document(sample_html_file)
        assert "<html>" not in doc.text
        assert "<p>" not in doc.text

    def test_load_html_single_page(self, sample_html_file: Path) -> None:
        doc = load_document(sample_html_file)
        assert len(doc.pages) == 1
        assert doc.metadata["format"] == "html"


class TestLoadPDF:
    """Tests for PDF loading."""

    def test_load_pdf_returns_pages(self, sample_pdf_file: Path) -> None:
        doc = load_document(sample_pdf_file)
        assert isinstance(doc, LoadedDocument)
        assert len(doc.pages) >= 1
        assert doc.pages[0].page_number == 1
        assert doc.metadata["format"] == "pdf"
        assert doc.metadata["page_count"] >= 1


class TestLoadDocumentErrors:
    """Tests for error handling."""

    def test_unsupported_file_type_raises(self, tmp_path: Path) -> None:
        f = tmp_path / "data.csv"
        f.write_text("a,b,c")
        with pytest.raises(ValueError, match="Unsupported file type"):
            load_document(f)

    def test_missing_file_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_document("/nonexistent/path/file.pdf")
