"""Neo4j graph database operations."""

import logging
from contextlib import contextmanager
from typing import Any, Generator

from neo4j import GraphDatabase, Session

from src.config import settings
from src.graph.schema import (
    NodeBase,
    NodeType,
    Relationship,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Connection management
# ---------------------------------------------------------------------------

_driver = None


def _get_driver():
    """Get or create the Neo4j driver singleton."""
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
    return _driver


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Context manager for a Neo4j session."""
    driver = _get_driver()
    session = driver.session()
    try:
        yield session
    finally:
        session.close()


def close_driver() -> None:
    """Close the Neo4j driver connection."""
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


# ---------------------------------------------------------------------------
# Node operations
# ---------------------------------------------------------------------------

def upsert_node(node: NodeBase) -> dict[str, Any]:
    """Create or update a node in the graph.

    Uses MERGE on (name) within the node's label to avoid duplicates.

    Args:
        node: The node to upsert.

    Returns:
        Dict with the node's properties as stored.
    """
    label = node.node_type.value
    props = {
        "name": node.name,
        "source": node.source,
        "confidence": node.confidence,
    }
    # Add type-specific fields (exclude base fields and empty strings)
    exclude_fields = {"node_type", "name", "source", "confidence", "properties"}
    for key, val in node.model_dump(exclude=exclude_fields).items():
        if val != "" and val != [] and val != {}:
            props[key] = val

    # Merge any extra properties
    for key, val in node.properties.items():
        props[key] = val

    query = f"""
    MERGE (n:{label} {{name: $name}})
    SET n += $props
    RETURN n
    """
    with get_session() as session:
        result = session.run(query, name=node.name, props=props)
        record = result.single()
        if record:
            return dict(record["n"])
    return {}


def upsert_nodes(nodes: list[NodeBase]) -> int:
    """Batch upsert multiple nodes.

    Args:
        nodes: List of nodes to upsert.

    Returns:
        Number of nodes upserted.
    """
    count = 0
    for node in nodes:
        upsert_node(node)
        count += 1
    logger.info("Upserted %d nodes", count)
    return count


def get_node(name: str, node_type: NodeType) -> dict[str, Any] | None:
    """Get a node by name and type.

    Args:
        name: The node name.
        node_type: The node type/label.

    Returns:
        Node properties dict, or None if not found.
    """
    label = node_type.value
    query = f"MATCH (n:{label} {{name: $name}}) RETURN n"
    with get_session() as session:
        result = session.run(query, name=name)
        record = result.single()
        if record:
            return dict(record["n"])
    return None


def delete_node(name: str, node_type: NodeType) -> bool:
    """Delete a node and all its relationships.

    Args:
        name: The node name.
        node_type: The node type/label.

    Returns:
        True if a node was deleted.
    """
    label = node_type.value
    query = f"MATCH (n:{label} {{name: $name}}) DETACH DELETE n RETURN count(n) AS deleted"
    with get_session() as session:
        result = session.run(query, name=name)
        record = result.single()
        return record is not None and record["deleted"] > 0


# ---------------------------------------------------------------------------
# Relationship operations
# ---------------------------------------------------------------------------

def upsert_relationship(rel: Relationship) -> dict[str, Any]:
    """Create or update a relationship between two nodes.

    Ensures both endpoint nodes exist (MERGE), then MERGE the relationship.

    Args:
        rel: The relationship to upsert.

    Returns:
        Dict with relationship properties.
    """
    source_label = rel.source_type.value
    target_label = rel.target_type.value
    rel_type = rel.relation_type.value

    props = {
        "source": rel.source,
        "confidence": rel.confidence,
    }
    props.update(rel.properties)

    query = f"""
    MERGE (a:{source_label} {{name: $source_name}})
    MERGE (b:{target_label} {{name: $target_name}})
    MERGE (a)-[r:{rel_type}]->(b)
    SET r += $props
    RETURN type(r) AS rel_type, r
    """
    with get_session() as session:
        result = session.run(
            query,
            source_name=rel.source_name,
            target_name=rel.target_name,
            props=props,
        )
        record = result.single()
        if record:
            return {"type": record["rel_type"], **dict(record["r"])}
    return {}


def upsert_relationships(rels: list[Relationship]) -> int:
    """Batch upsert multiple relationships.

    Args:
        rels: List of relationships to upsert.

    Returns:
        Number of relationships upserted.
    """
    count = 0
    for rel in rels:
        upsert_relationship(rel)
        count += 1
    logger.info("Upserted %d relationships", count)
    return count


# ---------------------------------------------------------------------------
# Query operations
# ---------------------------------------------------------------------------

def run_cypher(query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Execute a Cypher query and return results as list of dicts.

    Args:
        query: Cypher query string.
        params: Optional query parameters.

    Returns:
        List of result records as dicts.
    """
    with get_session() as session:
        result = session.run(query, **(params or {}))
        return [dict(record) for record in result]


def get_node_count() -> dict[str, int]:
    """Get count of nodes by label.

    Returns:
        Dict mapping label names to counts.
    """
    query = """
    CALL db.labels() YIELD label
    CALL apoc.cypher.run('MATCH (n:`' + label + '`) RETURN count(n) AS cnt', {}) YIELD value
    RETURN label, value.cnt AS count
    """
    # Fallback for environments without APOC
    try:
        results = run_cypher(query)
        return {r["label"]: r["count"] for r in results}
    except Exception:
        # Simple fallback: query each known label
        counts = {}
        for nt in NodeType:
            result = run_cypher(
                f"MATCH (n:{nt.value}) RETURN count(n) AS cnt"
            )
            if result:
                counts[nt.value] = result[0]["cnt"]
        return counts


def get_relationship_count() -> int:
    """Get total number of relationships in the graph.

    Returns:
        Total relationship count.
    """
    result = run_cypher("MATCH ()-[r]->() RETURN count(r) AS cnt")
    return result[0]["cnt"] if result else 0


def clear_graph() -> None:
    """Delete all nodes and relationships. Use with caution."""
    with get_session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    logger.warning("Cleared all nodes and relationships from graph")


def get_graph_stats() -> dict[str, Any]:
    """Get summary statistics for the graph.

    Returns:
        Dict with node counts by label and total relationship count.
    """
    return {
        "nodes": get_node_count(),
        "relationships": get_relationship_count(),
    }
