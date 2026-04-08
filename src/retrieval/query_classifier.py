"""Classify query type to route retrieval optimally."""

import logging
import re
from enum import Enum

from src.config import settings

logger = logging.getLogger(__name__)


class QueryType(str, Enum):
    """Types of queries the system can handle."""

    FACTUAL = "factual"
    RELATIONAL = "relational"
    ANALYTICAL = "analytical"
    REGULATORY = "regulatory"
    COMPARATIVE = "comparative"


# Pattern sets for rule-based classification
_RELATIONAL_PATTERNS = [
    r"\bwho\s+suppl",
    r"\bwho\s+produces?\b",
    r"\bwho\s+mines?\b",
    r"\bwho\s+operates?\b",
    r"\bsuppl(?:y|ies|ied)\s+(?:chain|to)\b",
    r"\bsource[ds]?\s+from\b",
    r"\bcompan(?:y|ies)\s+(?:that|which)\b",
    r"\bfacilit(?:y|ies)\s+(?:that|which)\b",
    r"\bconnect(?:ed|ion)\s+(?:to|between)\b",
    r"\brelationship\b",
    r"\bpath\s+from\b",
    r"\bupstream\b",
    r"\bdownstream\b",
]

_REGULATORY_PATTERNS = [
    r"\bDFARS\b",
    r"\bNDAA\b",
    r"\bDPA\b",
    r"\bTitle\s+III\b",
    r"\bregulat(?:ion|ory|ed)\b",
    r"\bcompliance\b",
    r"\bdeadline\b",
    r"\brestrict(?:ion|ed|s)\b",
    r"\bprohibit(?:ed|ion|s)\b",
    r"\bwaiver\b",
    r"\bexemption\b",
    r"\beffective\s+date\b",
    r"\blegislat(?:ion|ive)\b",
    r"\bstatut(?:e|ory)\b",
]

_COMPARATIVE_PATTERNS = [
    r"\bcompar(?:e|ing|ison)\b",
    r"\bversus\b",
    r"\b(?:vs\.?|v\.)\b",
    r"\bdifference\s+between\b",
    r"\bwhich\s+(?:is|has)\s+(?:more|greater|higher|lower|less)\b",
    r"\brank(?:ing|ed)?\b.*materials?\b",
    r"\bbetter\s+than\b",
]

_ANALYTICAL_PATTERNS = [
    r"\bwhat\s+(?:if|happens?\s+if|would\s+happen)\b",
    r"\bscenario\b",
    r"\bimpact\s+(?:of|on)\b",
    r"\bimplication\b",
    r"\bconsequence\b",
    r"\baffect(?:ed|s)?\b.*\bif\b",
    r"\brisk\s+(?:of|to|from)\b",
    r"\bvulnerabilit(?:y|ies)\b",
    r"\bcut(?:s|ting)?\s+(?:off|export)\b",
    r"\bdisrupt(?:ion|ed|s)?\b",
]


def _match_patterns(query: str, patterns: list[str]) -> int:
    """Count how many patterns match in the query."""
    query_lower = query.lower()
    return sum(1 for p in patterns if re.search(p, query_lower))


def classify_query_rules(query: str) -> QueryType | None:
    """Classify a query using rule-based heuristics.

    Args:
        query: The user's question.

    Returns:
        QueryType if classification is confident, None if ambiguous.
    """
    scores = {
        QueryType.RELATIONAL: _match_patterns(query, _RELATIONAL_PATTERNS),
        QueryType.REGULATORY: _match_patterns(query, _REGULATORY_PATTERNS),
        QueryType.COMPARATIVE: _match_patterns(query, _COMPARATIVE_PATTERNS),
        QueryType.ANALYTICAL: _match_patterns(query, _ANALYTICAL_PATTERNS),
    }

    best_type = max(scores, key=lambda t: scores[t])
    best_score = scores[best_type]

    # Need at least 1 match and a clear winner
    if best_score >= 1:
        second_best = sorted(scores.values(), reverse=True)[1]
        if best_score > second_best:
            return best_type

    # No strong signal — ambiguous
    return None


def classify_query_llm(query: str) -> QueryType:
    """Classify a query using an LLM call as fallback.

    Args:
        query: The user's question.

    Returns:
        Classified QueryType.
    """
    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=settings.anthropic_api_key)

        response = client.messages.create(
            model=settings.llm_model,
            max_tokens=50,
            messages=[{
                "role": "user",
                "content": (
                    "Classify this question into exactly one category. "
                    "Respond with ONLY the category name.\n\n"
                    "Categories:\n"
                    "- FACTUAL: asking for specific facts, numbers, data\n"
                    "- RELATIONAL: asking about supply chain connections, "
                    "who supplies/produces/operates what\n"
                    "- ANALYTICAL: what-if scenarios, impact analysis, risk\n"
                    "- REGULATORY: regulations, compliance, deadlines, DFARS, "
                    "NDAA, DPA\n"
                    "- COMPARATIVE: comparing materials, countries, companies\n\n"
                    f"Question: {query}"
                ),
            }],
        )

        raw = response.content[0].text.strip().upper()

        for qt in QueryType:
            if qt.value.upper() in raw:
                return qt

    except Exception as e:
        logger.warning("LLM classification failed, defaulting to FACTUAL: %s", e)

    return QueryType.FACTUAL


def classify_query(query: str) -> QueryType:
    """Classify a query using rules first, with LLM fallback for ambiguous cases.

    Args:
        query: The user's question.

    Returns:
        Classified QueryType.
    """
    # Try rule-based first
    result = classify_query_rules(query)
    if result is not None:
        logger.info("Query classified as %s (rules): '%s'", result.value, query[:80])
        return result

    # LLM fallback
    result = classify_query_llm(query)
    logger.info("Query classified as %s (LLM): '%s'", result.value, query[:80])
    return result
