#!/usr/bin/env python3
"""CLI script for ingesting documents into the knowledge base.

Usage:
    python scripts/ingest_documents.py --source data/raw/usgs/ --doc-type usgs_mcs
    python scripts/ingest_documents.py --source report.pdf --doc-type gao_report \
        --materials tungsten,nickel
"""

import argparse
import logging
import sys
from pathlib import Path

# Ensure the project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ingest.loader import SUPPORTED_EXTENSIONS
from src.ingest.pipeline import IngestionSummary, ingest_document

ALLOWED_DOC_TYPES = [
    "usgs_mcs",
    "gao_report",
    "crs_report",
    "dpa_announcement",
    "industry",
    "regulatory",
    "custom_analysis",
    "doe_report",
    "news",
]


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the CLI."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def collect_files(source: Path) -> list[Path]:
    """Collect all supported files from a path (file or directory).

    Args:
        source: A file path or directory path.

    Returns:
        List of file paths to ingest.
    """
    if source.is_file():
        if source.suffix.lower() in SUPPORTED_EXTENSIONS:
            return [source]
        else:
            logging.warning("Unsupported file type: %s", source)
            return []

    if source.is_dir():
        files = []
        for ext in SUPPORTED_EXTENSIONS:
            files.extend(source.rglob(f"*{ext}"))
        return sorted(files)

    logging.error("Path does not exist: %s", source)
    return []


def main() -> None:
    """Main entry point for the ingestion CLI."""
    parser = argparse.ArgumentParser(
        description="Ingest documents into the critical materials knowledge base."
    )
    parser.add_argument(
        "--source",
        type=str,
        required=True,
        help="Path to a file or directory of documents to ingest.",
    )
    parser.add_argument(
        "--doc-type",
        type=str,
        required=True,
        choices=ALLOWED_DOC_TYPES,
        help="Document type classification.",
    )
    parser.add_argument(
        "--materials",
        type=str,
        default="",
        help="Comma-separated list of materials (e.g., 'tungsten,nickel').",
    )
    parser.add_argument(
        "--source-url",
        type=str,
        default="",
        help="Source URL for the document(s).",
    )
    parser.add_argument(
        "--date-published",
        type=str,
        default=None,
        help="Publication date (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-ingestion (delete existing and re-ingest).",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose/debug logging.",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    source = Path(args.source)
    materials = (
        [m.strip() for m in args.materials.split(",") if m.strip()]
        if args.materials
        else None
    )

    files = collect_files(source)
    if not files:
        print(f"No supported files found at: {source}")
        sys.exit(1)

    print(f"Found {len(files)} file(s) to ingest as '{args.doc_type}'")
    print("-" * 60)

    summaries: list[IngestionSummary] = []
    for i, file_path in enumerate(files, start=1):
        print(f"[{i}/{len(files)}] Processing: {file_path.name}...", end=" ", flush=True)

        summary = ingest_document(
            file_path=file_path,
            document_type=args.doc_type,
            materials=materials,
            source_url=args.source_url,
            date_published=args.date_published,
            force=args.force,
        )
        summaries.append(summary)

        if summary.skipped:
            print(f"SKIPPED ({summary.skip_reason})")
        elif summary.errors:
            print(f"ERROR: {summary.errors[0]}")
        else:
            print(f"OK ({summary.chunks_created} chunks)")

    # Print summary
    print("-" * 60)
    total_files = len(summaries)
    successful = sum(1 for s in summaries if not s.skipped and not s.errors)
    skipped = sum(1 for s in summaries if s.skipped)
    failed = sum(1 for s in summaries if s.errors)
    total_chunks = sum(s.chunks_created for s in summaries)

    print(f"Total files:     {total_files}")
    print(f"Successful:      {successful}")
    print(f"Skipped (dupes): {skipped}")
    print(f"Failed:          {failed}")
    print(f"Total chunks:    {total_chunks}")


if __name__ == "__main__":
    main()
