"""Supabase-backed cache for fully-computed query responses.

The RAG pipeline is expensive — hybrid retrieval, cross-encoder rerank,
generation, verification, and follow-up question generation each make
one or more LLM / API calls that together cost $0.02-0.05 per fresh
query and take 5-15 seconds end-to-end. Demos repeat the same handful
of questions, so caching the full response by a hash of the normalized
inputs makes repeats instant and free.

Design notes:
    - Key is a sha256 of the lowercased, whitespace-normalized question
      plus sorted filter lists. Question punctuation is preserved since
      it can be meaningful ("what is X?" vs "what is X").
    - TTL is 24h. Short enough that corpus updates are reflected the
      next day without manual invalidation, long enough to absorb a
      full demo session's worth of repeated questions.
    - Cache errors are always swallowed with a warning log — the cache
      is a performance optimization, never a correctness dependency.
    - Multi-turn queries (those with conversation_context) are not
      cached because prior turns change the meaning of the current
      question; the caller is responsible for that skip.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from src.config import settings
from supabase import Client, create_client

logger = logging.getLogger(__name__)

_client: Client | None = None

CACHE_TTL_HOURS = 24


def _get_client() -> Client:
    """Get or create a Supabase client for cache operations."""
    global _client
    if _client is None:
        _client = create_client(
            settings.supabase_url, settings.supabase_service_key
        )
    return _client


def make_cache_key(
    question: str,
    materials: list[str] | None = None,
    doc_types: list[str] | None = None,
) -> str:
    """Build a deterministic cache key from the query inputs.

    Normalizes whitespace and case on the question so trivial
    formatting differences collide ("What  is tungsten?" and
    "what is tungsten?" hit the same cache entry). Filter lists are
    sorted so ["nickel", "tungsten"] and ["tungsten", "nickel"]
    collide as well.

    Args:
        question: The user's natural language question.
        materials: Optional material filters.
        doc_types: Optional document type filters.

    Returns:
        A hex sha256 digest usable as a primary key.
    """
    normalized_q = " ".join(question.lower().split())
    payload = json.dumps(
        {
            "q": normalized_q,
            "m": sorted(materials) if materials else [],
            "d": sorted(doc_types) if doc_types else [],
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def get_cached_response(cache_key: str) -> dict[str, Any] | None:
    """Look up a cached response by key.

    Only returns entries newer than CACHE_TTL_HOURS. Any Supabase
    error is logged and swallowed — a cache miss is indistinguishable
    from a cache failure to the caller, which is exactly what we want
    for a best-effort optimization.

    Args:
        cache_key: A key produced by make_cache_key().

    Returns:
        The cached response dict on hit, or None on miss / expiry /
        error.
    """
    try:
        cutoff = (
            datetime.now(timezone.utc) - timedelta(hours=CACHE_TTL_HOURS)
        ).isoformat()
        client = _get_client()
        result = (
            client.table("query_cache")
            .select("response, created_at")
            .eq("cache_key", cache_key)
            .gte("created_at", cutoff)
            .limit(1)
            .execute()
        )
        if not result.data:
            return None
        return result.data[0]["response"]
    except Exception as e:
        logger.warning("Cache lookup failed: %s", e)
        return None


def set_cached_response(
    cache_key: str,
    question: str,
    response: dict[str, Any],
) -> None:
    """Store a response under the cache key.

    Uses upsert so that re-running a query after the TTL window (or
    during dev) refreshes the cached entry in place. Errors are
    swallowed — a cache write failure must never break the pipeline.

    Args:
        cache_key: A key produced by make_cache_key().
        question: The original question (stored verbatim for
            debugging; the key is what determines collisions).
        response: The response payload to cache, already serialized
            to a JSON-compatible dict.
    """
    try:
        client = _get_client()
        client.table("query_cache").upsert(
            {
                "cache_key": cache_key,
                "question": question,
                "response": response,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ).execute()
    except Exception as e:
        logger.warning("Cache write failed: %s", e)
