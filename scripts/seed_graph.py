#!/usr/bin/env python3
"""CLI script for seeding the Neo4j knowledge graph with curated data.

Usage:
    python scripts/seed_graph.py
    python scripts/seed_graph.py --seed-file data/graph/seed_data.json
    python scripts/seed_graph.py --clear  # Clear graph first, then seed
    python scripts/seed_graph.py --stats  # Just print graph stats
"""

import argparse
import logging
import sys
from pathlib import Path

# Ensure the project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.graph.builder import build_graph_from_seed
from src.graph.neo4j_store import close_driver, get_graph_stats

DEFAULT_SEED_FILE = Path(__file__).resolve().parent.parent / "data" / "graph" / "seed_data.json"


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the CLI."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> None:
    """Main entry point for the graph seeding CLI."""
    parser = argparse.ArgumentParser(
        description="Seed the Neo4j knowledge graph with curated supply chain data."
    )
    parser.add_argument(
        "--seed-file",
        type=str,
        default=str(DEFAULT_SEED_FILE),
        help=f"Path to seed data JSON file (default: {DEFAULT_SEED_FILE})",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear all existing graph data before seeding.",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Print graph statistics and exit (no seeding).",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose/debug logging.",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    try:
        if args.stats:
            stats = get_graph_stats()
            print("Graph Statistics:")
            print(f"  Nodes: {stats.get('nodes', {})}")
            print(f"  Relationships: {stats.get('relationships', 0)}")
            return

        seed_path = Path(args.seed_file)
        if not seed_path.exists():
            print(f"Seed file not found: {seed_path}")
            sys.exit(1)

        if args.clear:
            print("Clearing existing graph data...")

        print(f"Seeding graph from: {seed_path}")
        result = build_graph_from_seed(seed_path, clear_existing=args.clear)

        print("-" * 60)
        print(f"Nodes upserted:         {result['nodes_upserted']}")
        print(f"Relationships upserted: {result['relationships_upserted']}")
        print(f"Graph stats:            {result['graph_stats']}")
        print("-" * 60)
        print("Graph seeding complete.")

    finally:
        close_driver()


if __name__ == "__main__":
    main()
