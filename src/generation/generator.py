"""LLM answer generation with citation-enforcing prompts via Claude API."""

import logging

from anthropic import Anthropic

from src.config import settings
from src.generation.prompts import (
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
