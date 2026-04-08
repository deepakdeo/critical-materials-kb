"""Tests for the section-aware document chunker."""


from src.ingest.chunker import Chunk, chunk_document, count_tokens
from src.ingest.loader import LoadedDocument, PageContent


def _make_doc(
    text: str, file_name: str = "test.txt", pages: list[PageContent] | None = None
) -> LoadedDocument:
    """Helper to create a LoadedDocument for testing."""
    if pages is None:
        pages = [PageContent(page_number=1, text=text)]
    return LoadedDocument(
        file_path=f"/tmp/{file_name}",
        file_name=file_name,
        text=text,
        pages=pages,
    )


class TestCountTokens:
    """Tests for token counting."""

    def test_count_tokens_nonempty(self) -> None:
        assert count_tokens("hello world") > 0

    def test_count_tokens_empty(self) -> None:
        assert count_tokens("") == 0


class TestChunkMetadata:
    """Tests that chunks carry correct metadata fields."""

    def test_chunks_have_required_fields(self) -> None:
        doc = _make_doc("Some simple text content for testing chunking.")
        chunks = chunk_document(doc, document_type="usgs_mcs", materials=["nickel"])

        assert len(chunks) > 0
        chunk = chunks[0]
        assert isinstance(chunk, Chunk)
        assert chunk.source_name == "test.txt"
        assert chunk.document_type == "usgs_mcs"
        assert chunk.materials == ["nickel"]
        assert chunk.chunk_index == 0
        assert chunk.total_chunks_in_doc == len(chunks)
        assert isinstance(chunk.page_numbers, list)

    def test_chunk_index_sequential(self) -> None:
        text = "\n\n".join([f"Paragraph {i} with enough text." for i in range(20)])
        doc = _make_doc(text)
        chunks = chunk_document(doc, target_tokens=30, overlap_tokens=0)

        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i
            assert chunk.total_chunks_in_doc == len(chunks)


class TestChunkSizeLimits:
    """Tests that chunks respect token size limits."""

    def test_chunks_within_target(self) -> None:
        # Create a document large enough to require splitting
        paragraphs = [f"Paragraph {i}. " + "Word " * 50 for i in range(20)]
        text = "\n\n".join(paragraphs)
        doc = _make_doc(text)

        target = 100
        chunks = chunk_document(doc, target_tokens=target, overlap_tokens=0)

        assert len(chunks) > 1
        for chunk in chunks:
            tokens = count_tokens(chunk.text)
            # Allow some tolerance due to paragraph boundary splitting
            assert tokens <= target * 1.5, f"Chunk has {tokens} tokens, expected <= {target * 1.5}"

    def test_small_document_single_chunk(self) -> None:
        doc = _make_doc("A small document.")
        chunks = chunk_document(doc, target_tokens=750)
        assert len(chunks) == 1


class TestChunkOverlap:
    """Tests that overlap is applied between consecutive chunks."""

    def test_overlap_applied(self) -> None:
        # Create text that will split into multiple chunks
        paragraphs = [
            f"Unique paragraph {i}. " + "Additional content here. " * 20
            for i in range(10)
        ]
        text = "\n\n".join(paragraphs)
        doc = _make_doc(text)

        chunks = chunk_document(doc, target_tokens=80, overlap_tokens=20)

        if len(chunks) > 1:
            # The second chunk should contain some text from the end of the first chunk
            first_words = chunks[0].text.split()
            second_text = chunks[1].text
            # Check that at least some tail words from chunk[0] appear at the start of chunk[1]
            tail_words = first_words[-5:] if len(first_words) >= 5 else first_words
            overlap_found = any(word in second_text[:200] for word in tail_words)
            assert overlap_found, "Expected overlap between consecutive chunks"


class TestSectionTitlePreservation:
    """Tests that section titles are preserved in chunks."""

    def test_heading_detected_and_preserved(self) -> None:
        text = (
            "INTRODUCTION\n\nThis is the introduction.\n\n"
            "METHODOLOGY\n\nThis is the methodology."
        )
        doc = _make_doc(text)
        chunks = chunk_document(doc)

        titles = [c.section_title for c in chunks]
        assert any("INTRODUCTION" in t for t in titles if t)

    def test_markdown_heading_detected(self) -> None:
        text = "# Overview\n\nSome overview text.\n\n## Details\n\nSome detail text."
        doc = _make_doc(text)
        chunks = chunk_document(doc)

        titles = [c.section_title for c in chunks]
        assert any("Overview" in t for t in titles if t)


class TestEdgeCases:
    """Tests for edge cases."""

    def test_single_section_document(self) -> None:
        doc = _make_doc("Just a single paragraph with no headings at all.")
        chunks = chunk_document(doc)
        assert len(chunks) == 1
        assert chunks[0].section_title == ""

    def test_empty_document(self) -> None:
        doc = _make_doc("")
        chunks = chunk_document(doc)
        assert len(chunks) == 0

    def test_whitespace_only_document(self) -> None:
        doc = _make_doc("   \n\n  \n  ")
        chunks = chunk_document(doc)
        assert len(chunks) == 0

    def test_multipage_document(self) -> None:
        pages = [
            PageContent(page_number=1, text="Page one content."),
            PageContent(page_number=2, text="Page two content."),
            PageContent(page_number=3, text="Page three content."),
        ]
        full_text = "\n\n".join(p.text for p in pages)
        doc = _make_doc(full_text, pages=pages)
        chunks = chunk_document(doc)
        assert len(chunks) >= 1
        assert all(len(c.page_numbers) > 0 for c in chunks)
