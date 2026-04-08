"""Section-aware document chunking with metadata preservation."""

import logging
import re

import tiktoken
from pydantic import BaseModel, Field

from src.config import settings
from src.ingest.loader import LoadedDocument

logger = logging.getLogger(__name__)

_tokenizer = tiktoken.get_encoding("cl100k_base")


class Chunk(BaseModel):
    """A single chunk of text with full provenance metadata."""

    text: str
    source_name: str = ""
    document_type: str = ""
    page_numbers: list[int] = Field(default_factory=list)
    section_title: str = ""
    materials: list[str] = Field(default_factory=list)
    chunk_index: int = 0
    total_chunks_in_doc: int = 0
    embedding: list[float] | None = None
    metadata: dict = Field(default_factory=dict)


def count_tokens(text: str) -> int:
    """Count the number of tokens in a text string.

    Args:
        text: Input text.

    Returns:
        Number of tokens.
    """
    return len(_tokenizer.encode(text))


def _decode_tokens(tokens: list[int]) -> str:
    """Decode a list of token IDs back to text."""
    return _tokenizer.decode(tokens)


def _encode(text: str) -> list[int]:
    """Encode text to token IDs."""
    return _tokenizer.encode(text)


def _is_heading(line: str) -> bool:
    """Detect if a line is likely a section heading.

    Heuristics:
    - Markdown-style headings (# Title)
    - All uppercase lines (common in PDF-extracted text)
    - Short lines ending with colon that start uppercase
    """
    stripped = line.strip()
    if not stripped or len(stripped) > 200:
        return False

    # Markdown-style headings
    if re.match(r"^#{1,3}\s+", stripped):
        return True

    # All uppercase lines (common in PDF-extracted text for headings)
    if stripped.isupper() and 3 < len(stripped) < 100:
        return True

    # Lines ending with a colon that are short (sub-headings)
    if (
        stripped.endswith(":")
        and len(stripped) < 80
        and not any(c.islower() for c in stripped[:5])
    ):
        return True

    return False


def _extract_heading_text(line: str) -> str:
    """Extract clean heading text from a heading line."""
    stripped = line.strip()
    stripped = re.sub(r"^#{1,3}\s+", "", stripped)
    return stripped


class Section(BaseModel):
    """A document section defined by a heading and its content."""

    title: str
    text: str
    page_numbers: list[int] = Field(default_factory=list)


class _PageMapper:
    """Maps character offsets in the full document text to page numbers."""

    def __init__(self, doc: LoadedDocument) -> None:
        self._offsets: list[tuple[int, int]] = []
        offset = 0
        for page in doc.pages:
            self._offsets.append((offset, page.page_number))
            offset += len(page.text) + 2  # +2 for "\n\n" join

    def get_page(self, char_offset: int) -> int:
        """Get page number for a character offset."""
        result = 1
        for off, pn in self._offsets:
            if off <= char_offset:
                result = pn
            else:
                break
        return result

    def get_pages_for_range(self, start: int, end: int) -> list[int]:
        """Get list of page numbers spanning a character range."""
        start_page = self.get_page(start)
        end_page = self.get_page(end)
        return list(range(start_page, end_page + 1))


def split_into_sections(doc: LoadedDocument) -> list[Section]:
    """Split a loaded document into sections based on headings.

    If a section exceeds 2x CHUNK_SIZE_TARGET tokens, it is further
    subdivided at paragraph boundaries to prevent oversized sections.

    Args:
        doc: The loaded document.

    Returns:
        List of sections with titles and text.
    """
    mapper = _PageMapper(doc)
    target = settings.chunk_size_target
    max_section_tokens = target * 2

    lines = doc.text.split("\n")
    raw_sections: list[Section] = []
    current_title = ""
    current_lines: list[str] = []
    current_char_offset = 0

    def _flush_section() -> None:
        text = "\n".join(current_lines).strip()
        if text:
            pages = mapper.get_pages_for_range(
                current_char_offset, current_char_offset + len(text)
            )
            raw_sections.append(
                Section(title=current_title, text=text, page_numbers=pages)
            )

    char_pos = 0
    for line in lines:
        if _is_heading(line):
            _flush_section()
            current_title = _extract_heading_text(line)
            current_lines = []
            current_char_offset = char_pos
        else:
            current_lines.append(line)
        char_pos += len(line) + 1

    _flush_section()

    # If no headings detected, treat whole doc as one section
    if not raw_sections and doc.text.strip():
        all_pages = [p.page_number for p in doc.pages]
        raw_sections.append(Section(
            title="", text=doc.text.strip(), page_numbers=all_pages
        ))

    # Subdivide oversized sections at paragraph boundaries
    sections: list[Section] = []
    for section in raw_sections:
        if count_tokens(section.text) <= max_section_tokens:
            sections.append(section)
            continue

        # Find the char offset of this section in the full document
        section_start = doc.text.find(section.text[:200])
        if section_start == -1:
            section_start = 0

        paragraphs = re.split(r"\n\s*\n", section.text)
        sub_parts: list[str] = []
        sub_token_count = 0
        sub_char_offset = section_start
        sub_index = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            para_tokens = count_tokens(para)

            if sub_token_count + para_tokens > max_section_tokens and sub_parts:
                sub_text = "\n\n".join(sub_parts)
                sub_end = sub_char_offset + len(sub_text)
                pages = mapper.get_pages_for_range(sub_char_offset, sub_end)
                sub_title = (
                    f"{section.title} (part {sub_index + 1})"
                    if section.title
                    else ""
                )
                sections.append(
                    Section(title=sub_title, text=sub_text, page_numbers=pages)
                )
                sub_char_offset = sub_end + 2
                sub_parts = []
                sub_token_count = 0
                sub_index += 1

            sub_parts.append(para)
            sub_token_count += para_tokens

        if sub_parts:
            sub_text = "\n\n".join(sub_parts)
            sub_end = sub_char_offset + len(sub_text)
            pages = mapper.get_pages_for_range(sub_char_offset, sub_end)
            sub_title = (
                f"{section.title} (part {sub_index + 1})"
                if section.title and sub_index > 0
                else section.title
            )
            sections.append(
                Section(title=sub_title, text=sub_text, page_numbers=pages)
            )

    logger.info(
        "Split document into %d sections (%d before subdivision)",
        len(sections),
        len(raw_sections),
    )
    return sections


def _split_section_into_chunks(
    section: Section,
    target_tokens: int,
    overlap_tokens: int,
    doc_text: str,
    page_mapper: _PageMapper,
) -> list[tuple[str, list[int]]]:
    """Split a section into token-bounded chunks with overlap.

    Computes per-chunk page numbers based on character position in the
    full document text rather than using the section's full page range.

    Args:
        section: The section to split.
        target_tokens: Target maximum tokens per chunk.
        overlap_tokens: Number of overlap tokens between consecutive chunks.
        doc_text: Full document text (for offset lookups).
        page_mapper: PageMapper for char offset → page number.

    Returns:
        List of (chunk_text, page_numbers) tuples.
    """
    section_tokens = count_tokens(section.text)
    if section_tokens <= target_tokens:
        return [(section.text, section.page_numbers)]

    # Find section offset in full document
    section_start = doc_text.find(section.text[:200])
    if section_start == -1:
        section_start = 0

    # Split into paragraphs
    paragraphs = re.split(r"\n\s*\n", section.text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    chunks: list[tuple[str, list[int]]] = []
    current_parts: list[str] = []
    current_token_count = 0
    current_char_len = 0

    def _flush_chunk(parts: list[str], char_len: int) -> None:
        chunk_text = "\n\n".join(parts)
        chunk_start = section_start + (
            section.text.find(parts[0][:50]) if parts else 0
        )
        chunk_end = chunk_start + char_len
        pages = page_mapper.get_pages_for_range(chunk_start, chunk_end)
        chunks.append((chunk_text, pages))

    for para in paragraphs:
        para_tokens = count_tokens(para)

        # If a single paragraph exceeds the target, split by sentences
        if para_tokens > target_tokens:
            if current_parts:
                _flush_chunk(current_parts, current_char_len)
                current_parts = []
                current_token_count = 0
                current_char_len = 0

            sentences = re.split(r"(?<=[.!?])\s+", para)
            sent_parts: list[str] = []
            sent_token_count = 0
            for sent in sentences:
                sent_tokens = count_tokens(sent)
                if sent_token_count + sent_tokens > target_tokens and sent_parts:
                    sent_text = " ".join(sent_parts)
                    s_start = section_start + section.text.find(
                        sent_parts[0][:50]
                    )
                    pages = page_mapper.get_pages_for_range(
                        s_start, s_start + len(sent_text)
                    )
                    chunks.append((sent_text, pages))
                    sent_parts = []
                    sent_token_count = 0
                sent_parts.append(sent)
                sent_token_count += sent_tokens
            if sent_parts:
                sent_text = " ".join(sent_parts)
                s_start = section_start + section.text.find(
                    sent_parts[0][:50]
                )
                pages = page_mapper.get_pages_for_range(
                    s_start, s_start + len(sent_text)
                )
                chunks.append((sent_text, pages))
            continue

        if current_token_count + para_tokens > target_tokens and current_parts:
            _flush_chunk(current_parts, current_char_len)
            current_parts = []
            current_token_count = 0
            current_char_len = 0

        current_parts.append(para)
        current_token_count += para_tokens
        current_char_len += len(para) + 2  # +2 for paragraph separator

    if current_parts:
        _flush_chunk(current_parts, current_char_len)

    # Apply overlap between consecutive chunks
    if len(chunks) > 1 and overlap_tokens > 0:
        overlapped: list[tuple[str, list[int]]] = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_text = chunks[i - 1][0]
            prev_tokens = _encode(prev_text)
            overlap_text = _decode_tokens(prev_tokens[-overlap_tokens:])
            new_text = overlap_text.strip() + " " + chunks[i][0]
            overlapped.append((new_text, chunks[i][1]))
        return overlapped

    return chunks


def chunk_document(
    doc: LoadedDocument,
    document_type: str = "",
    materials: list[str] | None = None,
    target_tokens: int | None = None,
    overlap_tokens: int | None = None,
) -> list[Chunk]:
    """Chunk a loaded document into section-aware chunks with metadata.

    Args:
        doc: The loaded document to chunk.
        document_type: Type of document (e.g., 'usgs_mcs', 'gao_report').
        materials: List of materials mentioned in this document.
        target_tokens: Override for chunk size target in tokens.
        overlap_tokens: Override for overlap between chunks in tokens.

    Returns:
        List of Chunk models with full metadata.
    """
    target = target_tokens or settings.chunk_size_target
    overlap = overlap_tokens or settings.chunk_overlap
    mats = materials or []

    sections = split_into_sections(doc)
    page_mapper = _PageMapper(doc)

    all_chunks: list[Chunk] = []
    for section in sections:
        sub_chunks = _split_section_into_chunks(
            section, target, overlap, doc.text, page_mapper
        )
        for chunk_text, page_nums in sub_chunks:
            all_chunks.append(Chunk(
                text=chunk_text,
                source_name=doc.file_name,
                document_type=document_type,
                page_numbers=page_nums,
                section_title=section.title,
                materials=mats,
            ))

    # Set chunk indices
    total = len(all_chunks)
    for i, chunk in enumerate(all_chunks):
        chunk.chunk_index = i
        chunk.total_chunks_in_doc = total

    logger.info(
        "Chunked '%s' into %d chunks (target=%d tokens, overlap=%d tokens)",
        doc.file_name, total, target, overlap,
    )
    return all_chunks
