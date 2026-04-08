"""Document loading for PDFs, HTML, and plain text files."""

import logging
import re
from pathlib import Path

import pdfplumber
from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".html", ".htm", ".txt"}


class PageContent(BaseModel):
    """A single page of extracted text."""

    page_number: int
    text: str


class LoadedDocument(BaseModel):
    """Standardized output from the document loader."""

    file_path: str
    file_name: str
    text: str = Field(description="Full concatenated text of the document")
    pages: list[PageContent] = Field(description="Per-page text content")
    metadata: dict = Field(default_factory=dict)


def load_pdf(file_path: Path) -> LoadedDocument:
    """Load a PDF file using pdfplumber with page-level text extraction.

    Args:
        file_path: Path to the PDF file.

    Returns:
        LoadedDocument with per-page text and full concatenated text.
    """
    pages: list[PageContent] = []
    with pdfplumber.open(file_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            pages.append(PageContent(page_number=i, text=text))

    full_text = "\n\n".join(p.text for p in pages if p.text)
    logger.info("Loaded PDF '%s': %d pages, %d chars", file_path.name, len(pages), len(full_text))

    return LoadedDocument(
        file_path=str(file_path),
        file_name=file_path.name,
        text=full_text,
        pages=pages,
        metadata={"format": "pdf", "page_count": len(pages)},
    )


_NAV_CLASS_PATTERNS = re.compile(
    r"(?i)(menu|sidebar|nav|navigation|breadcrumb|footer|header|"
    r"toolbar|topbar|bottom-bar|skip-link|cookie|banner|popup|modal)"
)

# HTML tags that typically contain navigation/boilerplate, not content
_STRIP_TAGS = ["script", "style", "nav", "header", "footer", "aside"]


def _is_nav_element(tag: Tag) -> bool:
    """Check if a tag is likely a navigation/boilerplate element by class or id."""
    for attr in ("class", "id", "role"):
        val = tag.get(attr, [])
        if isinstance(val, list):
            val = " ".join(val)
        if val and _NAV_CLASS_PATTERNS.search(val):
            return True
    return False


def load_html(file_path: Path) -> LoadedDocument:
    """Load an HTML file, stripping navigation and boilerplate elements.

    Removes <nav>, <header>, <footer>, <aside>, <script>, <style> tags,
    and elements with navigation-related class/id attributes (menu, sidebar,
    nav, breadcrumb, etc.) before extracting text.

    Args:
        file_path: Path to the HTML file.

    Returns:
        LoadedDocument with the extracted body text as a single page.
    """
    raw_html = file_path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(raw_html, "lxml")

    # Remove structural boilerplate tags
    for tag in soup(_STRIP_TAGS):
        tag.decompose()

    # Remove elements with navigation-related classes/ids
    # Collect first, then decompose to avoid modifying tree during iteration
    nav_tags = [
        tag for tag in soup.find_all(True)
        if isinstance(tag, Tag) and tag.attrs and _is_nav_element(tag)
    ]
    for tag in nav_tags:
        tag.decompose()

    body = soup.find("body")
    if body:
        text = body.get_text(separator="\n", strip=True)
    else:
        text = soup.get_text(separator="\n", strip=True)

    pages = [PageContent(page_number=1, text=text)]
    logger.info("Loaded HTML '%s': %d chars", file_path.name, len(text))

    return LoadedDocument(
        file_path=str(file_path),
        file_name=file_path.name,
        text=text,
        pages=pages,
        metadata={"format": "html"},
    )


def load_text(file_path: Path) -> LoadedDocument:
    """Load a plain text file.

    Args:
        file_path: Path to the text file.

    Returns:
        LoadedDocument with the full text as a single page.
    """
    text = file_path.read_text(encoding="utf-8", errors="replace")
    pages = [PageContent(page_number=1, text=text)]
    logger.info("Loaded TXT '%s': %d chars", file_path.name, len(text))

    return LoadedDocument(
        file_path=str(file_path),
        file_name=file_path.name,
        text=text,
        pages=pages,
        metadata={"format": "txt"},
    )


def load_document(file_path: str | Path) -> LoadedDocument:
    """Load a document from the given file path.

    Dispatches to the appropriate loader based on file extension.

    Args:
        file_path: Path to the document file.

    Returns:
        LoadedDocument with extracted text and metadata.

    Raises:
        ValueError: If the file extension is not supported.
        FileNotFoundError: If the file does not exist.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    loaders = {
        ".pdf": load_pdf,
        ".html": load_html,
        ".htm": load_html,
        ".txt": load_text,
    }

    return loaders[ext](path)
