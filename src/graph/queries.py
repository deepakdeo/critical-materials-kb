"""Pre-built Cypher query templates for common supply chain queries."""

from typing import Any

from src.graph.neo4j_store import run_cypher

# ---------------------------------------------------------------------------
# Query templates
# ---------------------------------------------------------------------------

def find_suppliers_of_material(material: str) -> list[dict[str, Any]]:
    """Find all companies that produce, mine, or process a material.

    Args:
        material: Material name (e.g., "tungsten").

    Returns:
        List of dicts with company info and relationship type.
    """
    query = """
    MATCH (c:Company)-[r:PRODUCES|MINES|PROCESSES]->(m:Material)
    WHERE toLower(m.name) CONTAINS toLower($material)
    RETURN c.name AS company, c.country AS country, c.sector AS sector,
           type(r) AS relationship, m.name AS material,
           r.confidence AS confidence
    ORDER BY r.confidence DESC
    """
    return run_cypher(query, {"material": material})


def find_materials_for_weapon_system(system_name: str) -> list[dict[str, Any]]:
    """Find materials a weapon system depends on.

    Args:
        system_name: Weapon system name.

    Returns:
        List of dicts with material info.
    """
    query = """
    MATCH (ws:WeaponSystem)-[r:DEPENDS_ON]->(m:Material)
    WHERE toLower(ws.name) CONTAINS toLower($system_name)
    RETURN ws.name AS weapon_system, m.name AS material,
           m.criticality_level AS criticality,
           r.confidence AS confidence
    ORDER BY m.name
    """
    return run_cypher(query, {"system_name": system_name})


def find_weapon_systems_using_material(material: str) -> list[dict[str, Any]]:
    """Find weapon systems that depend on a material.

    Args:
        material: Material name.

    Returns:
        List of dicts with weapon system info.
    """
    query = """
    MATCH (ws:WeaponSystem)-[r:DEPENDS_ON]->(m:Material)
    WHERE toLower(m.name) CONTAINS toLower($material)
    RETURN ws.name AS weapon_system, ws.platform_type AS platform_type,
           ws.service_branch AS service_branch, m.name AS material,
           r.confidence AS confidence
    ORDER BY ws.name
    """
    return run_cypher(query, {"material": material})


def find_supply_chain_for_material(material: str) -> list[dict[str, Any]]:
    """Get full supply chain for a material: countries, companies, facilities.

    Args:
        material: Material name.

    Returns:
        List of dicts describing the supply chain.
    """
    query = """
    MATCH (m:Material {name: $material})
    OPTIONAL MATCH (c:Country)-[r1:PRODUCES|EXPORTS]->(m)
    OPTIONAL MATCH (comp:Company)-[r2:PRODUCES|MINES|PROCESSES]->(m)
    OPTIONAL MATCH (comp)-[:LOCATED_IN]->(loc:Country)
    OPTIONAL MATCH (comp)-[:OPERATES]->(f:Facility)
    RETURN m.name AS material,
           collect(DISTINCT {country: c.name, role: type(r1)}) AS countries,
           collect(DISTINCT {
               company: comp.name, role: type(r2),
               location: loc.name, facility: f.name
           }) AS companies
    """
    return run_cypher(query, {"material": material})


def find_regulations_for_material(material: str) -> list[dict[str, Any]]:
    """Find regulations that apply to a material.

    Args:
        material: Material name.

    Returns:
        List of dicts with regulation info.
    """
    query = """
    MATCH (reg:Regulation)-[r:REGULATES|APPLIES_TO]->(m:Material)
    WHERE toLower(m.name) CONTAINS toLower($material)
    RETURN reg.name AS regulation, reg.regulation_type AS type,
           reg.effective_date AS effective_date, reg.status AS status,
           m.name AS material, type(r) AS relationship
    ORDER BY reg.name
    """
    return run_cypher(query, {"material": material})


def find_dpa_awards_for_material(material: str) -> list[dict[str, Any]]:
    """Find DPA Title III awards related to a material.

    Args:
        material: Material name.

    Returns:
        List of dicts with DPA award info.
    """
    query = """
    MATCH (d:DPAAward)-[:FUNDS]->(m:Material)
    WHERE toLower(m.name) CONTAINS toLower($material)
    OPTIONAL MATCH (d)-[:AWARDED_TO]->(c:Company)
    RETURN d.name AS award, d.amount AS amount, d.date_awarded AS date,
           d.purpose AS purpose, c.name AS company, m.name AS material
    ORDER BY d.date_awarded DESC
    """
    return run_cypher(query, {"material": material})


def find_companies_in_country(country: str) -> list[dict[str, Any]]:
    """Find all companies located in a country.

    Args:
        country: Country name.

    Returns:
        List of dicts with company info.
    """
    query = """
    MATCH (c:Company)-[:LOCATED_IN]->(co:Country)
    WHERE toLower(co.name) CONTAINS toLower($country)
    OPTIONAL MATCH (c)-[r:PRODUCES|MINES|PROCESSES]->(m:Material)
    RETURN c.name AS company, c.sector AS sector,
           collect(DISTINCT m.name) AS materials,
           co.name AS country
    ORDER BY c.name
    """
    return run_cypher(query, {"country": country})


def find_non_chinese_suppliers(material: str) -> list[dict[str, Any]]:
    """Find suppliers of a material NOT located in China.

    Args:
        material: Material name.

    Returns:
        List of non-Chinese supplier companies.
    """
    query = """
    MATCH (c:Company)-[r:PRODUCES|MINES|PROCESSES]->(m:Material)
    WHERE toLower(m.name) CONTAINS toLower($material)
    OPTIONAL MATCH (c)-[:LOCATED_IN]->(co:Country)
    WHERE co.name <> 'China'
    RETURN c.name AS company, co.name AS country, c.sector AS sector,
           type(r) AS role, m.name AS material
    ORDER BY c.name
    """
    return run_cypher(query, {"material": material})


def find_impact_of_country_disruption(
    country: str, material: str | None = None,
) -> list[dict[str, Any]]:
    """Find weapon systems affected if a country's supply is disrupted.

    Args:
        country: Country whose supply is disrupted.
        material: Optional material filter.

    Returns:
        List of affected weapon systems and the dependency chain.
    """
    material_filter = ""
    if material:
        material_filter = "AND toLower(m.name) CONTAINS toLower($material)"

    query = f"""
    MATCH (co:Country)-[:PRODUCES|EXPORTS]->(m:Material)<-[:DEPENDS_ON]-(ws:WeaponSystem)
    WHERE toLower(co.name) CONTAINS toLower($country)
    {material_filter}
    RETURN co.name AS country, m.name AS material,
           ws.name AS weapon_system, ws.platform_type AS platform_type,
           ws.service_branch AS service_branch
    ORDER BY m.name, ws.name
    """
    params: dict[str, Any] = {"country": country}
    if material:
        params["material"] = material
    return run_cypher(query, params)


# ---------------------------------------------------------------------------
# Generic graph search for the retriever
# ---------------------------------------------------------------------------

def search_graph(query_text: str, entities: list[str]) -> list[dict[str, Any]]:
    """Broad graph search matching any entities across all node types.

    Used by the graph retriever as a general-purpose fallback when
    specific query templates don't match.

    Args:
        query_text: The original query (unused, reserved for future NL→Cypher).
        entities: List of entity names to search for.

    Returns:
        List of dicts with matched nodes and their relationships.
    """
    if not entities:
        return []

    query = """
    UNWIND $entities AS entity_name
    CALL {
        WITH entity_name
        MATCH (n)
        WHERE toLower(n.name) CONTAINS toLower(entity_name)
        OPTIONAL MATCH (n)-[r]-(m)
        RETURN n, r, m, entity_name AS matched
        LIMIT 20
    }
    RETURN matched,
           labels(n) AS node_labels, n.name AS node_name,
           properties(n) AS node_props,
           type(r) AS rel_type,
           labels(m) AS neighbor_labels, m.name AS neighbor_name
    LIMIT 50
    """
    return run_cypher(query, {"entities": entities})
