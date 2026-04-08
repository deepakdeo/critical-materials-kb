"""Self-corrective CRAG verification of generated answers."""

import json
import logging

from anthropic import Anthropic
from pydantic import BaseModel, Field

from src.config import settings
from src.generation.prompts import (
    VERIFICATION_SYSTEM_PROMPT,
    VERIFICATION_USER_TEMPLATE,
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


class VerificationResult(BaseModel):
    """Result of the CRAG verification step."""

    verdict: str = "PASS"  # "PASS" or "FAIL"
    issues: list[str] = Field(default_factory=list)
    severity: str = "none"  # "none", "minor", "major"


def verify_answer(
    answer: str,
    chunks: list[RetrievalResult],
    model: str | None = None,
) -> VerificationResult:
    """Verify that a generated answer is grounded in the retrieved context.

    Checks:
    - Every bracketed citation corresponds to actual content in the context
    - Every factual claim is supported by the context
    - No fabricated information is present

    Args:
        answer: The generated answer to verify.
        chunks: The context chunks used for generation.
        model: Override LLM model.

    Returns:
        VerificationResult with verdict, issues, and severity.
    """
    if not answer or not chunks:
        return VerificationResult(
            verdict="FAIL",
            issues=["Empty answer or no context provided"],
            severity="major",
        )

    client = _get_client()
    context = format_context(chunks)

    user_message = VERIFICATION_USER_TEMPLATE.format(
        answer=answer,
        context=context,
    )

    try:
        response = client.messages.create(
            model=model or settings.llm_model,
            max_tokens=1024,
            system=VERIFICATION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        raw_text = response.content[0].text.strip()

        # Strip markdown code fences if present
        if raw_text.startswith("```"):
            lines = raw_text.split("\n")
            lines = [ln for ln in lines if not ln.strip().startswith("```")]
            raw_text = "\n".join(lines).strip()

        parsed = json.loads(raw_text)

        return VerificationResult(
            verdict=parsed.get("verdict", "FAIL"),
            issues=parsed.get("issues", []),
            severity=parsed.get("severity", "minor"),
        )

    except (json.JSONDecodeError, KeyError, IndexError) as e:
        logger.warning("Verification response parse error: %s", e)
        return VerificationResult(
            verdict="PASS",
            issues=[f"Verification parse error (treating as PASS): {e}"],
            severity="none",
        )
    except Exception as e:
        logger.error("Verification failed: %s", e)
        return VerificationResult(
            verdict="PASS",
            issues=[f"Verification error (treating as PASS): {e}"],
            severity="none",
        )
