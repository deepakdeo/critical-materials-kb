"""Tests for the query classifier (rule-based heuristics)."""

from src.retrieval.query_classifier import QueryType, classify_query_rules


class TestRuleBasedClassification:
    """Tests that rule-based patterns correctly classify queries."""

    def test_relational_who_supplies(self) -> None:
        result = classify_query_rules("Who supplies tungsten to the U.S.?")
        assert result == QueryType.RELATIONAL

    def test_relational_companies_that(self) -> None:
        result = classify_query_rules(
            "Which companies that produce rare earths are in Australia?"
        )
        assert result == QueryType.RELATIONAL

    def test_relational_supply_chain(self) -> None:
        result = classify_query_rules("What is the supply chain for cobalt?")
        assert result == QueryType.RELATIONAL

    def test_regulatory_dfars(self) -> None:
        result = classify_query_rules(
            "What does DFARS 225.7018 require for compliance?"
        )
        assert result == QueryType.REGULATORY

    def test_regulatory_restriction(self) -> None:
        result = classify_query_rules(
            "Is there a restriction on sourcing this material and a compliance deadline?"
        )
        assert result == QueryType.REGULATORY

    def test_regulatory_compliance(self) -> None:
        result = classify_query_rules(
            "Is there a compliance deadline for the new regulation?"
        )
        assert result == QueryType.REGULATORY

    def test_analytical_what_if(self) -> None:
        result = classify_query_rules(
            "What happens if China cuts tungsten exports?"
        )
        assert result == QueryType.ANALYTICAL

    def test_analytical_disruption(self) -> None:
        result = classify_query_rules(
            "What is the risk of disruption to cobalt supply?"
        )
        assert result == QueryType.ANALYTICAL

    def test_comparative_compare(self) -> None:
        result = classify_query_rules("Compare U.S. vs China tungsten production")
        assert result == QueryType.COMPARATIVE

    def test_ambiguous_returns_none(self) -> None:
        result = classify_query_rules("What is the current import reliance for nickel?")
        assert result is None

    def test_factual_plain_question(self) -> None:
        # A plain factual question shouldn't strongly match any specialized pattern
        result = classify_query_rules("How much tungsten does the U.S. produce annually?")
        assert result is None  # Falls through to LLM fallback


class TestQueryTypeEnum:
    """Tests for the QueryType enum values."""

    def test_all_values_present(self) -> None:
        expected = {"factual", "relational", "analytical", "regulatory", "comparative"}
        actual = {qt.value for qt in QueryType}
        assert actual == expected
