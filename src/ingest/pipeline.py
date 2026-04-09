"""End-to-end ingestion pipeline: load → chunk → embed → store."""

import hashlib
import logging
from pathlib import Path

from pydantic import BaseModel, Field

from src.ingest.chunker import Chunk, chunk_document
from src.ingest.embedder import embed_chunks
from src.ingest.loader import load_document
from src.store.metadata_store import create_document, delete_document, get_document_by_hash
from src.store.vector_store import delete_by_document_id, upsert_chunks

logger = logging.getLogger(__name__)


class IngestionSummary(BaseModel):
    """Summary of a single document ingestion."""

    file_path: str
    file_name: str
    file_hash: str
    chunks_created: int = 0
    skipped: bool = False
    skip_reason: str = ""
    document_id: str = ""
    entities_extracted: int = 0
    relationships_extracted: int = 0
    errors: list[str] = Field(default_factory=list)


def compute_file_hash(file_path: str | Path) -> str:
    """Compute SHA-256 hash of a file.

    Args:
        file_path: Path to the file.

    Returns:
        Hex string of the SHA-256 hash.
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for block in iter(lambda: f.read(8192), b""):
            sha256.update(block)
    return sha256.hexdigest()


def ingest_document(
    file_path: str | Path,
    document_type: str,
    materials: list[str] | None = None,
    source_url: str = "",
    date_published: str | None = None,
    force: bool = False,
    extract_entities: bool = False,
    entity_max_chunks: int = 10,
    entity_min_confidence: float = 0.7,
) -> IngestionSummary:
    """Ingest a single document through the full pipeline.

    Runs: loader → chunker → embedder → store (vector + metadata).
    Skips if a document with the same file hash already exists (unless force=True).

    Args:
        file_path: Path to the document file.
        document_type: Document type (e.g., 'usgs_mcs', 'gao_report').
        materials: Optional list of materials mentioned in the document.
        source_url: Optional source URL for the document.
        date_published: Optional publication date (YYYY-MM-DD).
        force: If True, delete existing document and re-ingest.

    Returns:
        IngestionSummary with details of what was processed.
    """
    path = Path(file_path)
    summary = IngestionSummary(
        file_path=str(path),
        file_name=path.name,
        file_hash="",
    )

    # Step 1: Compute file hash for deduplication
    try:
        file_hash = compute_file_hash(path)
        summary.file_hash = file_hash
    except FileNotFoundError:
        summary.errors.append(f"File not found: {path}")
        return summary

    # Step 2: Check for duplicate
    existing = get_document_by_hash(file_hash)
    if existing is not None:
        if force:
            # Delete existing document and its chunks, then re-ingest
            existing_id = existing.get("id", "")
            logger.info(
                "Force mode: deleting existing document %s (%s)",
                path.name, existing_id,
            )
            delete_by_document_id(existing_id)
            delete_document(existing_id)
        else:
            summary.skipped = True
            summary.skip_reason = (
                "Duplicate file (same SHA-256 hash already ingested)"
            )
            summary.document_id = existing.get("id", "")
            logger.info(
                "Skipping duplicate: %s (hash: %s)",
                path.name, file_hash[:12],
            )
            return summary

    # Step 3: Load document
    try:
        doc = load_document(path)
    except (ValueError, FileNotFoundError) as e:
        summary.errors.append(f"Load error: {e}")
        return summary

    # Step 4: Chunk document
    chunks: list[Chunk] = chunk_document(
        doc,
        document_type=document_type,
        materials=materials,
    )

    if not chunks:
        summary.errors.append("No chunks produced from document")
        return summary

    # Step 5: Generate embeddings
    try:
        chunks = embed_chunks(chunks)
    except RuntimeError as e:
        summary.errors.append(f"Embedding error: {e}")
        return summary

    # Step 6: Store document metadata
    try:
        doc_record = create_document(
            name=doc.file_name,
            document_type=document_type,
            file_path=str(path),
            file_hash=file_hash,
            total_chunks=len(chunks),
            materials=materials,
            source_url=source_url,
            date_published=date_published,
            metadata=doc.metadata,
        )
        summary.document_id = doc_record.get("id", "")
    except Exception as e:
        summary.errors.append(f"Metadata store error: {e}")
        return summary

    # Step 7: Store chunks with embeddings
    try:
        upsert_chunks(chunks, document_id=summary.document_id)
    except Exception as e:
        summary.errors.append(f"Vector store error: {e}")
        return summary

    summary.chunks_created = len(chunks)
    logger.info(
        "Ingested '%s': %d chunks, doc_id=%s",
        path.name,
        len(chunks),
        summary.document_id,
    )

    # Step 8 (optional): Extract entities and add to knowledge graph
    if extract_entities:
        try:
            from src.graph.builder import add_extracted_entities
            from src.ingest.entity_extractor import extract_entities_from_chunks

            nodes, rels = extract_entities_from_chunks(
                chunks, max_chunks=entity_max_chunks
            )
            if nodes or rels:
                result = add_extracted_entities(
                    nodes, rels, min_confidence=entity_min_confidence
                )
                summary.entities_extracted = result["nodes_added"]
                summary.relationships_extracted = result["relationships_added"]
                logger.info(
                    "Entity extraction for '%s': %d nodes, %d relationships added to graph",
                    path.name,
                    summary.entities_extracted,
                    summary.relationships_extracted,
                )
        except Exception as e:
            logger.warning("Entity extraction failed for '%s': %s", path.name, e)
            summary.errors.append(f"Entity extraction error (non-fatal): {e}")

    return summary
