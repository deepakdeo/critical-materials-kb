"""In-memory sliding-window rate limiter for expensive API endpoints.

Why this exists:
    The /api/query endpoint fans out to OpenAI (embeddings), Cohere
    (reranking), and Anthropic (generation + verification +
    follow-ups) on every cache miss — roughly $0.02-0.05 per call.
    Without a rate limit, a single abusive client or runaway script
    could drain the LLM budget in minutes, long before any alerting
    would fire. This module caps per-IP request rate so the damage
    from any one source is bounded.

Design notes:
    - Sliding window: we track a deque of request timestamps per IP
      and drop the ones that fall outside the window. This gives
      accurate rate enforcement even at the window edges, unlike a
      simple bucket-counter reset.
    - In-memory only. Render runs WEB_CONCURRENCY=1 on the Free tier,
      so a single process dict is sufficient. If we ever scale to
      multiple workers, this needs to move to Redis or similar.
    - Client IP is derived from X-Forwarded-For (which Render sets)
      with a fallback to request.client.host. Render's inbound proxy
      appends the real client IP as the first value in the chain.
    - We intentionally don't rate-limit /api/health or /api/sources
      — those are cheap and hitting them is harmless.
"""

import logging
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)

# 30 requests per 5-minute window per client IP. Generous enough for
# a real user exploring the tool (that's a query every 10 seconds,
# sustained), tight enough that an abusive script hits the ceiling
# within seconds and can't drain the LLM budget.
RATE_LIMIT_MAX_REQUESTS = 30
RATE_LIMIT_WINDOW_SECONDS = 5 * 60

_buckets: dict[str, deque[float]] = defaultdict(deque)
_lock = Lock()


def _client_ip(request: Request) -> str:
    """Derive the client IP, respecting Render's reverse proxy.

    Render's inbound proxy sets X-Forwarded-For to a comma-separated
    chain with the original client IP as the first entry. If that
    header is absent we fall back to the raw socket peer, which is
    correct in local dev but would rate-limit the proxy itself in
    production — so the header path is the important one.
    """
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def check_rate_limit(request: Request) -> None:
    """FastAPI dependency that raises 429 when a client exceeds the window.

    Usage:
        @router.post(
            "/query",
            dependencies=[Depends(check_rate_limit)],
        )
        def query_endpoint(...): ...

    Raises:
        HTTPException: 429 Too Many Requests if the caller has already
            made RATE_LIMIT_MAX_REQUESTS calls in the current window.
            The response includes a Retry-After header indicating
            when the oldest request in the window will expire.
    """
    ip = _client_ip(request)
    now = time.time()
    cutoff = now - RATE_LIMIT_WINDOW_SECONDS

    with _lock:
        bucket = _buckets[ip]
        # Evict timestamps older than the window.
        while bucket and bucket[0] < cutoff:
            bucket.popleft()

        if len(bucket) >= RATE_LIMIT_MAX_REQUESTS:
            retry_after = int(bucket[0] + RATE_LIMIT_WINDOW_SECONDS - now) + 1
            logger.warning(
                "Rate limit exceeded: ip=%s count=%d window=%ds",
                ip,
                len(bucket),
                RATE_LIMIT_WINDOW_SECONDS,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    "Too many requests. This demo runs on a limited "
                    "budget; please wait a few minutes before sending "
                    "more queries."
                ),
                headers={"Retry-After": str(retry_after)},
            )

        bucket.append(now)


def _reset_for_tests() -> None:
    """Clear all rate-limit state. For use in tests only."""
    with _lock:
        _buckets.clear()
