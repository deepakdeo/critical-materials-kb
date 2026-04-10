"""LLM answer generation with citation-enforcing prompts via Claude API."""

import logging

from anthropic import Anthropic

from src.config import settings
from src.generation.prompts import (
    FALLBACK_SYSTEM_PROMPT,
    FALLBACK_USER_TEMPLATE,
    GENERATION_SYSTEM_PROMPT,
    GENERATION_USER_TEMPLATE,
    format_context,
)
from src.retrieval.vector_retriever import RetrievalResult

logger = logging.getLogger(__name__)

_client: Anthropic | None = None


def _get_client() -> Anthropic:
    """Get or create an Anthropic client."""
    global _client
    if _client is None:
        _client = Anthropic(api_key=settings.anthropic_api_key)
    return _client


def generate_answer(
    question: str,
    chunks: list[RetrievalResult],
    model: str | None = None,
) -> str:
    """Generate a cited answer from retrieved context using Claude.

    Args:
        question: The user's question.
        chunks: Retrieved and reranked context chunks.
        model: Override LLM model (defaults to settings.llm_model).

    Returns:
        Generated answer string with source citations.
    """
    if not chunks:
        return (
            "The available documents do not contain sufficient information "
            "to answer this question."
        )

    client = _get_client()
    context = format_context(chunks)

    user_message = GENERATION_USER_TEMPLATE.format(
        context=context,
        question=question,
    )

    response = client.messages.create(
        model=model or settings.llm_model,
        max_tokens=2048,
        temperature=0,
        system=GENERATION_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    answer = response.content[0].text
    logger.info(
        "Generated answer (%d chars) using %d chunks for: '%s'",
        len(answer),
        len(chunks),
        question[:80],
    )
    return answer


def generate_fallback_answer(
    question: str,
    chunks: list[RetrievalResult],
    verification_issues: list[str],
    model: str | None = None,
) -> str:
    """Generate a graceful fallback when CRAG verification fails.

    Instead of returning a blunt "insufficient data" message, this asks the
    LLM to explain what the corpus DOES cover on this topic, suggest
    reformulated questions the corpus could answer, and point to specific
    source documents the analyst should read directly. The prompt forbids
    fabricating any new facts beyond what is in the retrieved context.

    Args:
        question: The original question that failed verification.
        chunks: The reranked context chunks from the failed attempt.
        verification_issues: The specific issues the verifier flagged.
        model: Override LLM model.

    Returns:
        A structured Markdown fallback response.
    """
    if not chunks:
        return (
            "**Why this question can't be answered with high confidence:**\n"
            "No relevant documents were retrieved from the corpus for this "
            "question. The topic may not be covered by the ingested sources, "
            "or the query may need to use different terminology.\n\n"
            "**Suggestion:** Try rephrasing with specific material names "
            "(e.g. tungsten, cobalt, rare earths), source types (DPA, DFARS, "
            "NDAA), or program/company names."
        )

    client = _get_client()
    context = format_context(chunks)
    issues_text = (
        "\n".join(f"- {issue}" for issue in verification_issues)
        if verification_issues
        else "- The generated answer could not be fully grounded in context."
    )

    user_message = FALLBACK_USER_TEMPLATE.format(
        question=question,
        issues=issues_text,
        context=context,
    )

    try:
        response = client.messages.create(
            model=model or settings.llm_model,
            max_tokens=1024,
            temperature=0,
            system=FALLBACK_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        fallback = response.content[0].text
        logger.info(
            "Generated fallback response (%d chars) for: '%s'",
            len(fallback),
            question[:80],
        )
        return fallback
    except Exception as e:
        logger.error("Fallback generation failed: %s", e)
        return (
            "**Why this question can't be answered with high confidence:**\n"
            "The generated answer could not be grounded in the retrieved "
            "source documents.\n\n"
            f"**Verification issues:** {'; '.join(verification_issues)}\n\n"
            "Try reformulating the question with more specific terminology, "
            "or browse the source documents directly."
        )
