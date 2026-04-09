"""Tests for the per-IP sliding-window rate limiter."""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from src.api import rate_limit
from src.api.rate_limit import (
    RATE_LIMIT_MAX_REQUESTS,
    _client_ip,
    check_rate_limit,
)


def _make_request(
    forwarded_for: str | None = None,
    client_host: str | None = "1.2.3.4",
) -> MagicMock:
    """Build a fake FastAPI Request with the given IP headers."""
    headers = {}
    if forwarded_for is not None:
        headers["x-forwarded-for"] = forwarded_for
    req = MagicMock()
    req.headers = headers
    if client_host is None:
        req.client = None
    else:
        req.client = MagicMock()
        req.client.host = client_host
    return req


class TestClientIp:
    """Tests for IP extraction."""

    def test_uses_x_forwarded_for(self) -> None:
        req = _make_request(forwarded_for="203.0.113.5")
        assert _client_ip(req) == "203.0.113.5"

    def test_takes_first_ip_in_forwarded_chain(self) -> None:
        """X-Forwarded-For may contain a chain; the original client is first."""
        req = _make_request(forwarded_for="203.0.113.5, 10.0.0.1, 10.0.0.2")
        assert _client_ip(req) == "203.0.113.5"

    def test_falls_back_to_client_host(self) -> None:
        req = _make_request(forwarded_for=None, client_host="5.6.7.8")
        assert _client_ip(req) == "5.6.7.8"

    def test_unknown_when_no_client(self) -> None:
        req = _make_request(forwarded_for=None, client_host=None)
        assert _client_ip(req) == "unknown"


class TestCheckRateLimit:
    """Tests for the rate limit dependency itself."""

    @pytest.fixture(autouse=True)
    def _reset(self) -> None:
        rate_limit._reset_for_tests()
        yield
        rate_limit._reset_for_tests()

    def test_allows_requests_under_limit(self) -> None:
        req = _make_request(forwarded_for="10.0.0.1")
        # RATE_LIMIT_MAX_REQUESTS - 1 calls should all pass.
        for _ in range(RATE_LIMIT_MAX_REQUESTS - 1):
            check_rate_limit(req)

    def test_blocks_request_at_limit(self) -> None:
        req = _make_request(forwarded_for="10.0.0.2")
        for _ in range(RATE_LIMIT_MAX_REQUESTS):
            check_rate_limit(req)
        with pytest.raises(HTTPException) as exc_info:
            check_rate_limit(req)
        assert exc_info.value.status_code == 429
        assert "Retry-After" in exc_info.value.headers

    def test_different_ips_tracked_separately(self) -> None:
        """Hitting the limit on one IP must not affect another."""
        req_a = _make_request(forwarded_for="10.0.0.3")
        req_b = _make_request(forwarded_for="10.0.0.4")
        for _ in range(RATE_LIMIT_MAX_REQUESTS):
            check_rate_limit(req_a)
        # IP A is exhausted, but IP B should still pass.
        check_rate_limit(req_b)

    def test_retry_after_header_is_positive(self) -> None:
        req = _make_request(forwarded_for="10.0.0.5")
        for _ in range(RATE_LIMIT_MAX_REQUESTS):
            check_rate_limit(req)
        with pytest.raises(HTTPException) as exc_info:
            check_rate_limit(req)
        retry_after = int(exc_info.value.headers["Retry-After"])
        assert retry_after > 0

    def test_window_eviction_releases_quota(self, monkeypatch) -> None:
        """Timestamps outside the window should be evicted, freeing quota."""
        import time as time_module

        fake_time = [1000.0]

        def fake_time_fn() -> float:
            return fake_time[0]

        monkeypatch.setattr(time_module, "time", fake_time_fn)

        req = _make_request(forwarded_for="10.0.0.6")
        for _ in range(RATE_LIMIT_MAX_REQUESTS):
            check_rate_limit(req)

        # Advance past the window so all prior timestamps are stale.
        fake_time[0] += rate_limit.RATE_LIMIT_WINDOW_SECONDS + 1

        # Should not raise — the bucket should have been evicted.
        check_rate_limit(req)
