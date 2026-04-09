"""Build the knowledge graph from seed data and extracted entities."""

import json
import logging
from pathlib import Path
from typing import Any

from src.graph.neo4j_store import (
    clear_graph,
    get_graph_stats,
    upsert_nodes,
    upsert_relationships,
)
from src.graph.schema import (
    NODE_MODELS,
    NodeBase,
    NodeType,
    Relationship,
    RelationType,
)

logger = logging.getLogger(__name__)


def _parse_node(data: dict[str, Any]) -> NodeBase:
    """Parse a node dict from seed data into the appropriate model.

    Args:
        data: Dict with at least 'name' and 'node_type' keys.

    Returns:
        Typed NodeBase subclass instance.
    """
    node_type = NodeType(data["node_type"])
    model_cls = NODE_MODELS[node_type]
    return model_cls(**data)


def _parse_relationship(data: dict[str, Any]) -> Relationship:
    """Parse a relationship dict from seed data.

    Args:
        data: Dict with source_name, source_type, target_name, target_type,
              relation_type keys.

    Returns:
        Relationship instance.
    """
    return Relationship(
        source_name=data["source_name"],
        source_type=NodeType(data["source_type"]),
        target_name=data["target_name"],
        target_type=NodeType(data["target_type"]),
        relation_type=RelationType(data["relation_type"]),
        source=data.get("source", "manual"),
        confidence=data.get("confidence", 1.0),
        properties=data.get("properties", {}),
    )


def load_seed_data(seed_path: str | Path) -> tuple[list[NodeBase], list[Relationship]]:
    """Load seed data from a JSON file.

    Expected format:
    {
        "nodes": [...],
        "relationships": [...]
    }

    Args:
        seed_path: Path to the seed data JSON file.

    Returns:
        Tuple of (nodes, relationships).
    """
    path = Path(seed_path)
    if not path.exists():
        raise FileNotFoundError(f"Seed data file not found: {path}")

    with open(path) as f:
        data = json.load(f)

    nodes = [_parse_node(n) for n in data.get("nodes", [])]
    rels = [_parse_relationship(r) for r in data.get("relationships", [])]

    logger.info("Loaded seed data: %d nodes, %d relationships", len(nodes), len(rels))
    return nodes, rels


def build_graph_from_seed(
    seed_path: str | Path,
    clear_existing: bool = False,
) -> dict[str, Any]:
    """Build the knowledge graph from seed data.

    Args:
        seed_path: Path to the seed data JSON file.
        clear_existing: If True, clear the graph before seeding.

    Returns:
        Dict with build statistics.
    """
    if clear_existing:
        clear_graph()

    nodes, rels = load_seed_data(seed_path)

    node_count = upsert_nodes(nodes)
    rel_count = upsert_relationships(rels)

    stats = get_graph_stats()
    logger.info(
        "Graph built: %d nodes upserted, %d relationships upserted. "
        "Total: %s nodes, %d relationships",
        node_count, rel_count,
        stats.get("nodes", {}), stats.get("relationships", 0),
    )

    return {
        "nodes_upserted": node_count,
        "relationships_upserted": rel_count,
        "graph_stats": stats,
    }


def add_extracted_entities(
    nodes: list[NodeBase],
    relationships: list[Relationship],
    min_confidence: float = 0.7,
) -> dict[str, int]:
    """Add auto-extracted entities to the graph.

    Only adds entities above the minimum confidence threshold.
    All entities are tagged with source='auto-extracted'.

    Args:
        nodes: List of extracted nodes.
        relationships: List of extracted relationships.
        min_confidence: Minimum confidence to include (default 0.7).

    Returns:
        Dict with counts of added nodes and relationships.
    """
    filtered_nodes = [n for n in nodes if n.confidence >= min_confidence]
    filtered_rels = [r for r in relationships if r.confidence >= min_confidence]

    skipped_nodes = len(nodes) - len(filtered_nodes)
    skipped_rels = len(relationships) - len(filtered_rels)

    if skipped_nodes or skipped_rels:
        logger.info(
            "Filtered out %d nodes and %d relationships below confidence %.2f",
            skipped_nodes, skipped_rels, min_confidence,
        )

    node_count = upsert_nodes(filtered_nodes) if filtered_nodes else 0
    rel_count = upsert_relationships(filtered_rels) if filtered_rels else 0

    return {"nodes_added": node_count, "relationships_added": rel_count}
