"""Graph-based retrieval for relational queries."""

import logging
import re
from typing import Any

from src.graph.queries import (
    find_dpa_awards_for_material,
    find_impact_of_country_disruption,
    find_non_chinese_suppliers,
    find_regulations_for_material,
    find_suppliers_of_material,
    find_supply_chain_for_material,
    find_weapon_systems_using_material,
    search_graph,
)
from src.retrieval.vector_retriever import RetrievalResult

logger = logging.getLogger(__name__)

# Known material names for entity extraction from queries
_MATERIALS = [
    "tungsten", "nickel", "cobalt", "lithium", "rare earth", "neodymium",
    "dysprosium", "titanium", "tantalum", "gallium", "germanium", "graphite",
    "aluminum", "copper", "platinum", "magnesium", "manganese", "chromium",
]

_COUNTRIES = [
    "china", "united states", "russia", "congo", "australia", "canada",
    "chile", "south africa", "vietnam", "bolivia", "rwanda", "portugal",
    "austria",
]


def _extract_entities(query: str) -> dict[str, list[str]]:
    """Extract material and country names from a query string.

    Args:
        query: The user's question.

    Returns:
        Dict with 'materials' and 'countries' lists.
    """
    q_lower = query.lower()
    materials = [m for m in _MATERIALS if m in q_lower]
    countries = [c for c in _COUNTRIES if c in q_lower]
    return {"materials": materials, "countries": countries}


def _format_graph_results(results: list[dict[str, Any]], query_type: str) -> str:
    """Format graph query results into readable text for the LLM.

    Args:
        results: Raw results from graph queries.
        query_type: Type of query for formatting context.

    Returns:
        Formatted string of graph results.
    """
    if not results:
        return ""

    lines = [f"[Graph Knowledge — {query_type}]"]
    for r in results:
        parts = []
        for key, val in r.items():
            if val is not None and val != "" and val != []:
                parts.append(f"{key}: {val}")
        if parts:
            lines.append("  - " + " | ".join(parts))

    return "\n".join(lines)


def graph_search(query: str) -> list[RetrievalResult]:
    """Execute graph-based retrieval for a query.

    Extracts entities from the query, runs appropriate graph queries,
    and returns results as RetrievalResult objects that can be merged
    with vector/BM25 results.

    Args:
        query: The user's natural language question.

    Returns:
        List of RetrievalResult objects from graph traversal.
    """
    entities = _extract_entities(query)
    materials = entities["materials"]
    countries = entities["countries"]

    if not materials and not countries:
        # Try generic graph search with any capitalized words as entities
        words = re.findall(r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*", query)
        if words:
            results = search_graph(query, words)
            if results:
                text = _format_graph_results(results, "general search")
                return [_to_retrieval_result(text, "graph_search", 0.6)]
        return []

    all_results: list[RetrievalResult] = []
    q_lower = query.lower()

    for material in materials:
        # Supplier queries
        supplier_terms = ["supplier", "supplie", "produce", "who", "company", "companies"]
        if any(term in q_lower for term in supplier_terms):
            results = find_suppliers_of_material(material)
            if results:
                text = _format_graph_results(results, f"suppliers of {material}")
                all_results.append(_to_retrieval_result(text, f"suppliers_{material}", 0.85))

        # Non-Chinese supplier queries
        non_china_terms = ["non-chinese", "not china", "without china", "alternative", "domestic"]
        if any(term in q_lower for term in non_china_terms):
            results = find_non_chinese_suppliers(material)
            if results:
                text = _format_graph_results(results, f"non-Chinese suppliers of {material}")
                all_results.append(_to_retrieval_result(text, f"non_chinese_{material}", 0.9))

        # Weapon system dependency queries
        weapon_terms = ["weapon", "defense", "military", "dod", "program", "affected", "system"]
        if any(term in q_lower for term in weapon_terms):
            results = find_weapon_systems_using_material(material)
            if results:
                text = _format_graph_results(results, f"weapon systems using {material}")
                all_results.append(_to_retrieval_result(text, f"weapons_{material}", 0.85))

        # Supply chain queries
        if any(term in q_lower for term in ["supply chain", "chain", "sourced", "source"]):
            results = find_supply_chain_for_material(material)
            if results:
                text = _format_graph_results(results, f"supply chain for {material}")
                all_results.append(_to_retrieval_result(text, f"chain_{material}", 0.8))

        # Regulation queries
        if any(term in q_lower for term in ["regulat", "dfars", "ndaa", "restrict", "compliance"]):
            results = find_regulations_for_material(material)
            if results:
                text = _format_graph_results(results, f"regulations for {material}")
                all_results.append(_to_retrieval_result(text, f"regs_{material}", 0.8))

        # DPA award queries
        if any(term in q_lower for term in ["dpa", "title iii", "award", "fund"]):
            results = find_dpa_awards_for_material(material)
            if results:
                text = _format_graph_results(results, f"DPA awards for {material}")
                all_results.append(_to_retrieval_result(text, f"dpa_{material}", 0.85))

    # Country disruption queries
    for country in countries:
        if any(term in q_lower for term in ["cut", "disrupt", "ban", "restrict", "export", "if"]):
            mat_filter = materials[0] if materials else None
            results = find_impact_of_country_disruption(country, mat_filter)
            if results:
                text = _format_graph_results(results, f"impact of {country} disruption")
                all_results.append(_to_retrieval_result(text, f"disruption_{country}", 0.9))

    # Fallback: if we have materials but no specific query pattern matched, get suppliers
    if materials and not all_results:
        for material in materials:
            results = find_suppliers_of_material(material)
            if results:
                text = _format_graph_results(results, f"suppliers of {material}")
                all_results.append(_to_retrieval_result(text, f"suppliers_{material}", 0.7))

    logger.info(
        "Graph search: %d results for query with materials=%s, countries=%s",
        len(all_results), materials, countries,
    )
    return all_results


def _to_retrieval_result(text: str, source_id: str, score: float) -> RetrievalResult:
    """Convert graph text to a RetrievalResult.

    Args:
        text: Formatted graph results text.
        source_id: Identifier for the graph query source.
        score: Relevance score.

    Returns:
        RetrievalResult instance.
    """
    return RetrievalResult(
        text=text,
        score=score,
        page_numbers=[],
        section_title="Knowledge Graph",
        metadata={
            "source_name": "Knowledge Graph",
            "document_type": "graph",
            "graph_query": source_id,
        },
    )
