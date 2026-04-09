"""Tests for the CRAG fallback answer generator.

The fallback path runs when verification FAILs twice and replaces the blunt
"insufficient data" message with a structured response that reports what the
corpus DOES cover and suggests reformulated questions. These tests patch the
Anthropic client so they don't require network / API keys.
"""

from unittest.mock import MagicMock, patch

from src.generation import generator
from src.generation.generator import generate_fallback_answer
from src.retrieval.vector_retriever import RetrievalResult


def _make_chunk(
    source_name: str = "mcs2025.pdf",
    pages: list[int] | None = None,
    text: str = "The U.S. imports 79% of its tungsten from China.",
) -> RetrievalResult:
    return RetrievalResult(
        text=text,
        score=0.8,
        page_numbers=pages or [132],
        section_title="Tungsten",
        metadata={"source_name": source_name, "document_type": "usgs_mcs"},
    )


def _mock_anthropic_response(text: str) -> MagicMock:
    """Build a mock Anthropic response with the given text content."""
    response = MagicMock()
    response.content = [MagicMock(text=text)]
    return response


class TestGenerateFallbackAnswer:
    """Tests for generate_fallback_answer."""

    def setup_method(self) -> None:
        # Reset the cached client between tests so patches apply cleanly.
        generator._client = None

    def test_empty_chunks_returns_static_message(self) -> None:
        """With no retrieved chunks, return a static message without calling the LLM."""
        result = generate_fallback_answer(
            question="What is the stockpile level?",
            chunks=[],
            verification_issues=["no grounding"],
        )
        assert "can't be answered" in result.lower() or "cannot" in result.lower()
        assert "rephrasing" in result.lower() or "reformulate" in result.lower()

    def test_calls_llm_with_question_and_context(self) -> None:
        """Verify the LLM is called with the question, issues, and context."""
        chunks = [_make_chunk()]
        mock_response = _mock_anthropic_response(
            "**Why this question can't be answered with high confidence:**\n"
            "The docs lack specific stockpile figures.\n\n"
            "**What the retrieved documents DO cover on this topic:**\n"
            "- U.S. tungsten import dependency\n\n"
            "**Questions this corpus could likely answer instead:**\n"
            "- What is U.S. tungsten import reliance?\n\n"
            "**Documents worth reading directly:**\n"
            "- mcs2025.pdf, p.132"
        )
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        with patch.object(generator, "_get_client", return_value=mock_client):
            result = generate_fallback_answer(
                question="How long will tungsten stockpiles last?",
                chunks=chunks,
                verification_issues=["Citation does not support claim"],
            )

        assert mock_client.messages.create.called
        call_kwargs = mock_client.messages.create.call_args.kwargs
        user_msg = call_kwargs["messages"][0]["content"]
        assert "How long will tungsten stockpiles last?" in user_msg
        assert "Citation does not support claim" in user_msg
        assert "79% of its tungsten from China" in user_msg  # context passthrough
        assert "Why this question can't be answered" in result

    def test_handles_empty_issues_list(self) -> None:
        """Should still work if verification_issues is empty."""
        chunks = [_make_chunk()]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_anthropic_response(
            "**Why this question can't be answered with high confidence:**\nGap.\n"
        )
        with patch.object(generator, "_get_client", return_value=mock_client):
            result = generate_fallback_answer(
                question="Test?",
                chunks=chunks,
                verification_issues=[],
            )
        assert result  # non-empty
        user_msg = mock_client.messages.create.call_args.kwargs[
            "messages"
        ][0]["content"]
        # When issues are empty the template substitutes a default line
        assert "could not be fully grounded" in user_msg

    def test_llm_exception_returns_graceful_fallback(self) -> None:
        """If the LLM call itself fails, return a static message with the issues."""
        chunks = [_make_chunk()]
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = RuntimeError("API down")

        with patch.object(generator, "_get_client", return_value=mock_client):
            result = generate_fallback_answer(
                question="Test?",
                chunks=chunks,
                verification_issues=["some issue"],
            )
        assert "high confidence" in result
        assert "some issue" in result

    def test_uses_fallback_system_prompt(self) -> None:
        """Verify the fallback system prompt (not the normal generation prompt) is used."""
        chunks = [_make_chunk()]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_anthropic_response("ok")

        with patch.object(generator, "_get_client", return_value=mock_client):
            generate_fallback_answer(
                question="Test?",
                chunks=chunks,
                verification_issues=["x"],
            )

        system_prompt = mock_client.messages.create.call_args.kwargs["system"]
        # The fallback prompt explicitly forbids answering the original question
        assert "NOT to answer the original question" in system_prompt
        assert "DO NOT fabricate" in system_prompt
