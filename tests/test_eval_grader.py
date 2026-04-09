"""Tests for the eval-harness grading logic.

These tests validate the rubric-based grader without hitting the real query
pipeline. A fake response object stands in for QueryResponse so we can
exercise each check (verdict, confidence, must_cite_any, must_mention_any,
must_not_contain) in isolation.
"""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.run_eval import GOLDEN_SET_PATH, grade_response, load_golden_set


def _fake_response(
    answer: str = "",
    verdict: str = "PASS",
    severity: str = "none",
    confidence: float = 0.9,
    source_names: list[str] | None = None,
    is_fallback: bool = False,
) -> SimpleNamespace:
    """Build a stand-in for QueryResponse with the minimal attributes the grader reads."""
    sources = [SimpleNamespace(name=n) for n in (source_names or [])]
    return SimpleNamespace(
        answer=answer,
        verification=SimpleNamespace(verdict=verdict, severity=severity),
        sources=sources,
        metadata={
            "confidence": confidence,
            "is_fallback": is_fallback,
            "retrieval_method": "hybrid",
            "latency_ms": 1234,
        },
    )


class TestGradeResponseVerdict:
    def test_verdict_pass_matches(self) -> None:
        q = {"expected_verdict": "PASS", "min_confidence": 0.0}
        r = _fake_response(verdict="PASS")
        grade = grade_response(q, r)
        assert grade["checks"]["verdict"] is True

    def test_fail_major_does_not_match_pass(self) -> None:
        q = {"expected_verdict": "PASS", "min_confidence": 0.0}
        r = _fake_response(verdict="FAIL", severity="major")
        grade = grade_response(q, r)
        assert grade["checks"]["verdict"] is False
        assert grade["passed"] is False

    def test_fail_minor_counts_as_pass(self) -> None:
        """FAIL(minor) is a verifier nitpick, not a failed answer.

        Users see a yellow badge and a functional answer — for grading
        purposes this is a PASS outcome.
        """
        q = {"expected_verdict": "PASS", "min_confidence": 0.0}
        r = _fake_response(verdict="FAIL", severity="minor")
        grade = grade_response(q, r)
        assert grade["checks"]["verdict"] is True

    def test_fail_expected_matches_fail_any_severity(self) -> None:
        q = {"expected_verdict": "FAIL", "min_confidence": 0.0}
        r = _fake_response(verdict="FAIL", severity="major")
        grade = grade_response(q, r)
        assert grade["checks"]["verdict"] is True

    def test_fail_expected_rejects_pass(self) -> None:
        q = {"expected_verdict": "FAIL", "min_confidence": 0.0}
        r = _fake_response(verdict="PASS")
        grade = grade_response(q, r)
        assert grade["checks"]["verdict"] is False


class TestGradeResponseConfidence:
    def test_confidence_above_threshold(self) -> None:
        q = {"min_confidence": 0.7}
        r = _fake_response(confidence=0.85)
        grade = grade_response(q, r)
        assert grade["checks"]["min_confidence"] is True

    def test_confidence_below_threshold(self) -> None:
        q = {"min_confidence": 0.7}
        r = _fake_response(confidence=0.50)
        grade = grade_response(q, r)
        assert grade["checks"]["min_confidence"] is False

    def test_confidence_exactly_at_threshold(self) -> None:
        q = {"min_confidence": 0.7}
        r = _fake_response(confidence=0.7)
        grade = grade_response(q, r)
        assert grade["checks"]["min_confidence"] is True


class TestGradeResponseMustCite:
    def test_one_of_required_sources_present(self) -> None:
        q = {"must_cite_any": ["mcs2025.pdf", "mcs2026.pdf"]}
        r = _fake_response(source_names=["mcs2026.pdf", "gao-24-107176.pdf"])
        grade = grade_response(q, r)
        assert grade["checks"]["must_cite_any"] is True

    def test_no_required_source_present(self) -> None:
        q = {"must_cite_any": ["mcs2025.pdf"]}
        r = _fake_response(source_names=["kennametal-defense.html"])
        grade = grade_response(q, r)
        assert grade["checks"]["must_cite_any"] is False

    def test_empty_requirement_passes(self) -> None:
        q = {"must_cite_any": []}
        r = _fake_response(source_names=[])
        grade = grade_response(q, r)
        assert grade["checks"]["must_cite_any"] is True


class TestGradeResponseMustMention:
    def test_keyword_present(self) -> None:
        q = {"must_mention_any": ["tungsten", "China"]}
        r = _fake_response(
            answer="The U.S. imports 80% of its tungsten from China."
        )
        grade = grade_response(q, r)
        assert grade["checks"]["must_mention_any"] is True

    def test_keyword_case_insensitive(self) -> None:
        q = {"must_mention_any": ["CHINA"]}
        r = _fake_response(answer="china is the largest producer")
        grade = grade_response(q, r)
        assert grade["checks"]["must_mention_any"] is True

    def test_no_keyword_present(self) -> None:
        q = {"must_mention_any": ["nickel"]}
        r = _fake_response(answer="Tungsten is used in armor-piercing rounds.")
        grade = grade_response(q, r)
        assert grade["checks"]["must_mention_any"] is False


class TestGradeResponseMustNotContain:
    def test_forbidden_phrase_absent(self) -> None:
        q = {"must_not_contain": ["will last exactly"]}
        r = _fake_response(
            answer="The stockpile size is not disclosed in public documents."
        )
        grade = grade_response(q, r)
        assert grade["checks"]["must_not_contain"] is True

    def test_forbidden_phrase_present(self) -> None:
        q = {"must_not_contain": ["will last exactly"]}
        r = _fake_response(answer="The stockpile will last exactly 12 months.")
        grade = grade_response(q, r)
        assert grade["checks"]["must_not_contain"] is False


class TestGradeResponseOverall:
    def test_all_checks_pass_means_question_passes(self) -> None:
        q = {
            "expected_verdict": "PASS",
            "min_confidence": 0.7,
            "must_cite_any": ["mcs2026.pdf"],
            "must_mention_any": ["tungsten"],
            "must_not_contain": [],
        }
        r = _fake_response(
            answer="Tungsten is a critical material.",
            verdict="PASS",
            confidence=0.85,
            source_names=["mcs2026.pdf"],
        )
        grade = grade_response(q, r)
        assert grade["passed"] is True
        assert all(grade["checks"].values())

    def test_any_check_fail_means_question_fails(self) -> None:
        q = {
            "expected_verdict": "PASS",
            "min_confidence": 0.7,
            "must_cite_any": ["mcs2026.pdf"],
            "must_mention_any": ["tungsten"],
            "must_not_contain": [],
        }
        # Missing the required citation
        r = _fake_response(
            answer="Tungsten is a critical material.",
            verdict="PASS",
            confidence=0.85,
            source_names=["other.pdf"],
        )
        grade = grade_response(q, r)
        assert grade["passed"] is False

    def test_actual_payload_populated(self) -> None:
        q = {"expected_verdict": "PASS", "min_confidence": 0.0}
        r = _fake_response(
            answer="A" * 500,
            verdict="PASS",
            confidence=0.82,
            source_names=["a.pdf", "b.pdf"],
            is_fallback=False,
        )
        grade = grade_response(q, r)
        assert grade["actual"]["verdict"] == "PASS"
        assert grade["actual"]["confidence"] == 0.82
        assert grade["actual"]["is_fallback"] is False
        assert set(grade["actual"]["sources_cited"]) == {"a.pdf", "b.pdf"}
        # Answer preview is truncated
        assert len(grade["actual"]["answer_preview"]) <= 200


class TestGoldenSetIntegrity:
    """Validate the golden set JSON file itself is well-formed."""

    def test_golden_set_loads(self) -> None:
        questions = load_golden_set()
        assert len(questions) > 0

    def test_every_question_has_required_fields(self) -> None:
        questions = load_golden_set()
        # expected_verdict is optional (may be null for unanswerable questions
        # where the right behavior is either refuse-as-PASS or catch-as-FAIL
        # and content checks do the real validation).
        required = {"id", "category", "question", "min_confidence"}
        for q in questions:
            missing = required - set(q.keys())
            assert not missing, f"{q.get('id')} missing fields: {missing}"

    def test_ids_are_unique(self) -> None:
        questions = load_golden_set()
        ids = [q["id"] for q in questions]
        assert len(ids) == len(set(ids))

    def test_categories_are_known(self) -> None:
        questions = load_golden_set()
        known = {
            "factual", "relational", "analytical",
            "regulatory", "comparative", "unanswerable",
        }
        for q in questions:
            assert q["category"] in known, (
                f"Unknown category {q['category']} in {q['id']}"
            )

    def test_verdicts_are_valid(self) -> None:
        questions = load_golden_set()
        for q in questions:
            verdict = q.get("expected_verdict")
            assert verdict in {"PASS", "FAIL", None}

    def test_unanswerable_questions_rely_on_content_checks(self) -> None:
        """Unanswerable questions should use content-level checks, not verdict.

        A well-behaved system refuses with "insufficient information" which
        legitimately passes verification — so verdict is not a reliable
        signal. Instead, enforce refusal keywords in must_mention_any.
        """
        questions = load_golden_set()
        refusal_keywords = {
            "insufficient", "cannot", "not", "unable", "unknown",
            "does not", "no specific", "unavailable", "classified",
            "predict", "future",
        }
        for q in questions:
            if q["category"] != "unanswerable":
                continue
            # expected_verdict must be null/absent for unanswerable
            assert q.get("expected_verdict") is None, (
                f"{q['id']}: unanswerable questions should omit "
                f"expected_verdict (got {q.get('expected_verdict')!r})"
            )
            # must_mention_any must contain at least one refusal keyword
            mentions = {m.lower() for m in q.get("must_mention_any", [])}
            assert mentions & refusal_keywords, (
                f"{q['id']}: unanswerable must require at least one "
                f"refusal keyword in must_mention_any"
            )

    def test_file_is_valid_json(self) -> None:
        """Catch JSON syntax errors separately from schema issues."""
        with Path(GOLDEN_SET_PATH).open() as f:
            data = json.load(f)
        assert "questions" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
