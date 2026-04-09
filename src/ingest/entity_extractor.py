"""LLM-based entity and relationship extraction from document chunks."""

import json
import logging

from anthropic import Anthropic

from src.config import settings
from src.graph.schema import (
    NODE_MODELS,
    NodeBase,
    NodeType,
    Relationship,
    RelationType,
)
from src.ingest.chunker import Chunk

logger = logging.getLogger(__name__)

_EXTRACTION_PROMPT = (
    "You are an expert at extracting structured supply chain data from government "
    "and industry documents about critical materials.\n\n"
    "Extract entities and relationships from the text below. Focus on:\n"
    "- Materials (critical materials, minerals, metals)\n"
    "- Companies (producers, suppliers, manufacturers)\n"
    "- Countries (producers, exporters, importers)\n"
    "- Facilities (mines, refineries, smelters, factories)\n"
    "- Weapon Systems (defense platforms that use critical materials)\n"
    "- Regulations (DFARS, NDAA, executive orders, DPA)\n"
    "- DPA Awards (Defense Production Act Title III awards)\n\n"
    "For each entity, provide:\n"
    "- name: canonical name\n"
    "- node_type: one of Material, Company, Country, Facility, "
    "WeaponSystem, Regulation, DPAAward\n"
    "- confidence: 0.0-1.0 how confident you are this is correct\n"
    "- Any relevant type-specific fields\n\n"
    "For each relationship, provide:\n"
    "- source_name, source_type, target_name, target_type\n"
    "- relation_type: one of PRODUCES, SUPPLIES, MINES, PROCESSES, IMPORTS, "
    "EXPORTS, LOCATED_IN, OPERATES, DEPENDS_ON, MANUFACTURED_BY, "
    "REGULATES, APPLIES_TO, AWARDED_TO, FUNDS\n"
    "- confidence: 0.0-1.0\n\n"
    "Respond with ONLY valid JSON in this exact format:\n"
    '{"nodes": [...], "relationships": [...]}\n\n'
    "If no entities are found, return: "
    '{"nodes": [], "relationships": []}\n\n'
    "TEXT:\n"
)


def _parse_extraction_response(raw: str) -> tuple[list[NodeBase], list[Relationship]]:
    """Parse the LLM JSON response into typed models.

    Args:
        raw: Raw JSON string from LLM.

    Returns:
        Tuple of (nodes, relationships).
    """
    # Strip markdown code fences if present
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    data = json.loads(text)

    nodes: list[NodeBase] = []
    for n in data.get("nodes", []):
        try:
            node_type = NodeType(n["node_type"])
            model_cls = NODE_MODELS[node_type]
            n["source"] = "auto-extracted"
            nodes.append(model_cls(**n))
        except (KeyError, ValueError) as e:
            logger.debug("Skipping invalid node %s: %s", n.get("name", "?"), e)

    relationships: list[Relationship] = []
    for r in data.get("relationships", []):
        try:
            relationships.append(Relationship(
                source_name=r["source_name"],
                source_type=NodeType(r["source_type"]),
                target_name=r["target_name"],
                target_type=NodeType(r["target_type"]),
                relation_type=RelationType(r["relation_type"]),
                source="auto-extracted",
                confidence=r.get("confidence", 0.7),
                properties=r.get("properties", {}),
            ))
        except (KeyError, ValueError) as e:
            logger.debug(
                "Skipping invalid relationship %s->%s: %s",
                r.get("source_name", "?"), r.get("target_name", "?"), e,
            )

    return nodes, relationships


def extract_entities_from_chunk(chunk: Chunk) -> tuple[list[NodeBase], list[Relationship]]:
    """Extract entities and relationships from a single chunk using Claude.

    Args:
        chunk: The document chunk to extract from.

    Returns:
        Tuple of (nodes, relationships) extracted.
    """
    client = Anthropic(api_key=settings.anthropic_api_key)

    context = f"Source: {chunk.source_name}"
    if chunk.section_title:
        context += f" | Section: {chunk.section_title}"
    if chunk.materials:
        context += f" | Known materials: {', '.join(chunk.materials)}"

    response = client.messages.create(
        model=settings.llm_model,
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": f"{_EXTRACTION_PROMPT}{context}\n\n{chunk.text}",
        }],
    )

    raw = response.content[0].text
    try:
        nodes, rels = _parse_extraction_response(raw)
        logger.info(
            "Extracted %d nodes, %d relationships from chunk %d of '%s'",
            len(nodes), len(rels), chunk.chunk_index, chunk.source_name,
        )
        return nodes, rels
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(
            "Failed to parse extraction from chunk %d of '%s': %s",
            chunk.chunk_index, chunk.source_name, e,
        )
        return [], []


def extract_entities_from_chunks(
    chunks: list[Chunk],
    max_chunks: int | None = None,
) -> tuple[list[NodeBase], list[Relationship]]:
    """Extract entities from multiple chunks.

    Args:
        chunks: List of chunks to process.
        max_chunks: Optional limit on chunks to process (for cost control).

    Returns:
        Tuple of (all_nodes, all_relationships) combined from all chunks.
    """
    to_process = chunks[:max_chunks] if max_chunks else chunks
    all_nodes: list[NodeBase] = []
    all_rels: list[Relationship] = []

    for i, chunk in enumerate(to_process):
        logger.info(
            "Extracting entities from chunk %d/%d (%s)",
            i + 1, len(to_process), chunk.source_name,
        )
        nodes, rels = extract_entities_from_chunk(chunk)
        all_nodes.extend(nodes)
        all_rels.extend(rels)

    logger.info(
        "Total extraction: %d nodes, %d relationships from %d chunks",
        len(all_nodes), len(all_rels), len(to_process),
    )
    return all_nodes, all_rels
