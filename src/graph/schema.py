"""Knowledge graph schema: node and relationship type definitions."""

from enum import Enum

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Node types
# ---------------------------------------------------------------------------

class NodeType(str, Enum):
    """Types of nodes in the knowledge graph."""

    MATERIAL = "Material"
    COMPANY = "Company"
    COUNTRY = "Country"
    FACILITY = "Facility"
    WEAPON_SYSTEM = "WeaponSystem"
    REGULATION = "Regulation"
    DPA_AWARD = "DPAAward"


class NodeBase(BaseModel):
    """Base fields shared by all node types."""

    name: str
    node_type: NodeType
    source: str = Field(default="manual", description="'manual' or 'auto-extracted'")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    properties: dict = Field(default_factory=dict)


class MaterialNode(NodeBase):
    """A critical material (e.g., tungsten, cobalt, rare earths)."""

    node_type: NodeType = NodeType.MATERIAL
    category: str = ""  # e.g., "metal", "mineral", "rare earth"
    criticality_level: str = ""  # e.g., "critical", "strategic", "near-critical"


class CompanyNode(NodeBase):
    """A company in the supply chain."""

    node_type: NodeType = NodeType.COMPANY
    country: str = ""
    sector: str = ""  # e.g., "mining", "processing", "manufacturing", "defense"


class CountryNode(NodeBase):
    """A country involved in supply or consumption."""

    node_type: NodeType = NodeType.COUNTRY
    role: str = ""  # e.g., "producer", "consumer", "processor"


class FacilityNode(NodeBase):
    """A physical facility (mine, refinery, factory)."""

    node_type: NodeType = NodeType.FACILITY
    facility_type: str = ""  # e.g., "mine", "refinery", "smelter", "factory"
    location: str = ""
    country: str = ""


class WeaponSystemNode(NodeBase):
    """A defense/weapon system that depends on critical materials."""

    node_type: NodeType = NodeType.WEAPON_SYSTEM
    platform_type: str = ""  # e.g., "aircraft", "missile", "ship", "vehicle"
    service_branch: str = ""  # e.g., "Army", "Navy", "Air Force"


class RegulationNode(NodeBase):
    """A regulation or policy (DFARS, NDAA section, executive order)."""

    node_type: NodeType = NodeType.REGULATION
    regulation_type: str = ""  # e.g., "DFARS", "NDAA", "EO", "DPA"
    effective_date: str = ""
    status: str = ""  # e.g., "active", "pending", "proposed"


class DPAAwardNode(NodeBase):
    """A Defense Production Act Title III award."""

    node_type: NodeType = NodeType.DPA_AWARD
    amount: str = ""
    date_awarded: str = ""
    purpose: str = ""


# Map NodeType enum to model class
NODE_MODELS: dict[NodeType, type[NodeBase]] = {
    NodeType.MATERIAL: MaterialNode,
    NodeType.COMPANY: CompanyNode,
    NodeType.COUNTRY: CountryNode,
    NodeType.FACILITY: FacilityNode,
    NodeType.WEAPON_SYSTEM: WeaponSystemNode,
    NodeType.REGULATION: RegulationNode,
    NodeType.DPA_AWARD: DPAAwardNode,
}


# ---------------------------------------------------------------------------
# Relationship types
# ---------------------------------------------------------------------------

class RelationType(str, Enum):
    """Types of relationships (edges) in the knowledge graph."""

    # Supply chain
    PRODUCES = "PRODUCES"            # Company/Country → Material
    SUPPLIES = "SUPPLIES"            # Company → Company
    MINES = "MINES"                  # Company → Material
    PROCESSES = "PROCESSES"          # Company → Material
    IMPORTS = "IMPORTS"              # Country → Material
    EXPORTS = "EXPORTS"             # Country → Material

    # Location
    LOCATED_IN = "LOCATED_IN"        # Facility/Company → Country
    OPERATES = "OPERATES"            # Company → Facility

    # Defense dependencies
    DEPENDS_ON = "DEPENDS_ON"        # WeaponSystem → Material
    MANUFACTURED_BY = "MANUFACTURED_BY"  # WeaponSystem → Company

    # Regulatory
    REGULATES = "REGULATES"          # Regulation → Material
    APPLIES_TO = "APPLIES_TO"        # Regulation → Company/Material
    AWARDED_TO = "AWARDED_TO"        # DPAAward → Company
    FUNDS = "FUNDS"                  # DPAAward → Material/Facility


class Relationship(BaseModel):
    """A directed relationship between two nodes."""

    source_name: str
    source_type: NodeType
    target_name: str
    target_type: NodeType
    relation_type: RelationType
    source: str = Field(default="manual", description="'manual' or 'auto-extracted'")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    properties: dict = Field(default_factory=dict)


# Valid relationship patterns: (source_type, relation_type, target_type)
VALID_RELATIONSHIPS: list[tuple[NodeType, RelationType, NodeType]] = [
    # Supply chain
    (NodeType.COMPANY, RelationType.PRODUCES, NodeType.MATERIAL),
    (NodeType.COMPANY, RelationType.MINES, NodeType.MATERIAL),
    (NodeType.COMPANY, RelationType.PROCESSES, NodeType.MATERIAL),
    (NodeType.COMPANY, RelationType.SUPPLIES, NodeType.COMPANY),
    (NodeType.COUNTRY, RelationType.PRODUCES, NodeType.MATERIAL),
    (NodeType.COUNTRY, RelationType.IMPORTS, NodeType.MATERIAL),
    (NodeType.COUNTRY, RelationType.EXPORTS, NodeType.MATERIAL),

    # Location
    (NodeType.FACILITY, RelationType.LOCATED_IN, NodeType.COUNTRY),
    (NodeType.COMPANY, RelationType.LOCATED_IN, NodeType.COUNTRY),
    (NodeType.COMPANY, RelationType.OPERATES, NodeType.FACILITY),

    # Defense
    (NodeType.WEAPON_SYSTEM, RelationType.DEPENDS_ON, NodeType.MATERIAL),
    (NodeType.WEAPON_SYSTEM, RelationType.MANUFACTURED_BY, NodeType.COMPANY),

    # Regulatory
    (NodeType.REGULATION, RelationType.REGULATES, NodeType.MATERIAL),
    (NodeType.REGULATION, RelationType.APPLIES_TO, NodeType.COMPANY),
    (NodeType.REGULATION, RelationType.APPLIES_TO, NodeType.MATERIAL),
    (NodeType.DPA_AWARD, RelationType.AWARDED_TO, NodeType.COMPANY),
    (NodeType.DPA_AWARD, RelationType.FUNDS, NodeType.MATERIAL),
    (NodeType.DPA_AWARD, RelationType.FUNDS, NodeType.FACILITY),
]
