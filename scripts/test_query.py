#!/usr/bin/env python3
"""CLI script for quick query testing against the RAG pipeline.

Usage:
    python scripts/test_query.py "What is U.S. import reliance for tungsten?"
    python scripts/test_query.py "Who supplies tungsten to General Dynamics?" --verbose
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.generation.chains import query


def main() -> None:
    """Main entry point for the query test CLI."""
    parser = argparse.ArgumentParser(
        description="Test a query against the critical materials RAG pipeline."
    )
    parser.add_argument("question", type=str, help="The question to ask.")
    parser.add_argument(
        "--materials",
        type=str,
        default="",
        help="Comma-separated material filters.",
    )
    parser.add_argument(
        "--doc-types",
        type=str,
        default="",
        help="Comma-separated document type filters.",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON response.",
    )

    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    materials = (
        [m.strip() for m in args.materials.split(",") if m.strip()]
        if args.materials
        else None
    )
    doc_types = (
        [d.strip() for d in args.doc_types.split(",") if d.strip()]
        if args.doc_types
        else None
    )

    print(f"Question: {args.question}")
    print("=" * 70)

    response = query(
        question=args.question,
        materials=materials,
        doc_types=doc_types,
    )

    if args.json:
        print(response.model_dump_json(indent=2))
        return

    # Pretty print
    print(f"\nAnswer:\n{response.answer}")
    print(f"\n{'=' * 70}")
    print(f"Query type: {response.metadata.get('query_type', 'N/A')}")
    print(f"Retrieval:  {response.metadata.get('retrieval_method', 'N/A')}")
    print(
        f"Chunks:     {response.metadata.get('chunks_retrieved', 0)} retrieved"
        f" → {response.metadata.get('chunks_after_rerank', 0)} after rerank"
    )
    print(f"Latency:    {response.metadata.get('latency_ms', 0)}ms")
    print(
        f"Verified:   {response.verification.verdict} "
        f"(severity: {response.verification.severity})"
    )

    if response.verification.issues:
        print(f"Issues:     {'; '.join(response.verification.issues)}")

    if response.sources:
        print(f"\nSources ({len(response.sources)}):")
        for i, src in enumerate(response.sources, 1):
            print(f"  {i}. {src.name} {src.page} — {src.section}")


if __name__ == "__main__":
    main()
