"""Tests for the Supabase-backed query response cache."""

from unittest.mock import MagicMock, patch

import pytest

from src.store import query_cache
from src.store.query_cache import (
    get_cached_response,
    make_cache_key,
    set_cached_response,
)


class TestMakeCacheKey:
    """Tests for the cache key normalization function."""

    def test_identical_inputs_collide(self) -> None:
        k1 = make_cache_key("What is tungsten?", ["tungsten"], ["usgs_mcs"])
        k2 = make_cache_key("What is tungsten?", ["tungsten"], ["usgs_mcs"])
        assert k1 == k2

    def test_whitespace_normalized(self) -> None:
        k1 = make_cache_key("What  is   tungsten?")
        k2 = make_cache_key("What is tungsten?")
        assert k1 == k2

    def test_case_normalized(self) -> None:
        k1 = make_cache_key("WHAT IS TUNGSTEN?")
        k2 = make_cache_key("what is tungsten?")
        assert k1 == k2

    def test_filter_order_normalized(self) -> None:
        k1 = make_cache_key("q", ["tungsten", "nickel"])
        k2 = make_cache_key("q", ["nickel", "tungsten"])
        assert k1 == k2

    def test_doc_type_filter_affects_key(self) -> None:
        k1 = make_cache_key("q", None, ["usgs_mcs"])
        k2 = make_cache_key("q", None, ["gao_report"])
        assert k1 != k2

    def test_question_difference_affects_key(self) -> None:
        k1 = make_cache_key("What is tungsten?")
        k2 = make_cache_key("What is nickel?")
        assert k1 != k2

    def test_none_and_empty_filters_equivalent(self) -> None:
        k1 = make_cache_key("q", None, None)
        k2 = make_cache_key("q", [], [])
        assert k1 == k2

    def test_punctuation_preserved(self) -> None:
        """Punctuation can be meaningful — don't collapse it."""
        k1 = make_cache_key("What is tungsten?")
        k2 = make_cache_key("What is tungsten")
        assert k1 != k2

    def test_key_is_hex_sha256(self) -> None:
        key = make_cache_key("q")
        assert len(key) == 64
        int(key, 16)  # Raises if not hex.


class TestGetCachedResponse:
    """Tests for cache retrieval."""

    @pytest.fixture(autouse=True)
    def _reset_client(self) -> None:
        """Ensure each test gets a fresh mock client."""
        query_cache._client = None
        yield
        query_cache._client = None

    def test_hit_returns_response(self) -> None:
        fake_response = {"answer": "cached", "metadata": {}}
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value \
            .gte.return_value.limit.return_value.execute.return_value.data = [
                {"response": fake_response, "created_at": "2026-04-09T00:00:00Z"}
            ]
        with patch.object(query_cache, "_get_client", return_value=mock_client):
            result = get_cached_response("some_key")
        assert result == fake_response

    def test_miss_returns_none(self) -> None:
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value \
            .gte.return_value.limit.return_value.execute.return_value.data = []
        with patch.object(query_cache, "_get_client", return_value=mock_client):
            result = get_cached_response("some_key")
        assert result is None

    def test_supabase_error_returns_none(self) -> None:
        """Cache must never break the pipeline — swallow all errors."""
        mock_client = MagicMock()
        mock_client.table.side_effect = RuntimeError("network down")
        with patch.object(query_cache, "_get_client", return_value=mock_client):
            result = get_cached_response("some_key")
        assert result is None

    def test_ttl_filter_applied(self) -> None:
        """The query must use .gte() against a cutoff timestamp."""
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value \
            .gte.return_value.limit.return_value.execute.return_value.data = []
        with patch.object(query_cache, "_get_client", return_value=mock_client):
            get_cached_response("some_key")
        # gte should have been called once with a created_at cutoff
        gte_call = mock_client.table.return_value.select.return_value.eq \
            .return_value.gte.call_args
        assert gte_call.args[0] == "created_at"
        # The cutoff should parse as an ISO timestamp
        from datetime import datetime
        datetime.fromisoformat(gte_call.args[1].replace("Z", "+00:00"))


class TestSetCachedResponse:
    """Tests for cache writes."""

    @pytest.fixture(autouse=True)
    def _reset_client(self) -> None:
        query_cache._client = None
        yield
        query_cache._client = None

    def test_upserts_row(self) -> None:
        mock_client = MagicMock()
        with patch.object(query_cache, "_get_client", return_value=mock_client):
            set_cached_response(
                "some_key", "What is tungsten?", {"answer": "..."}
            )
        mock_client.table.assert_called_once_with("query_cache")
        upsert_payload = (
            mock_client.table.return_value.upsert.call_args.args[0]
        )
        assert upsert_payload["cache_key"] == "some_key"
        assert upsert_payload["question"] == "What is tungsten?"
        assert upsert_payload["response"] == {"answer": "..."}
        assert "created_at" in upsert_payload

    def test_supabase_error_swallowed(self) -> None:
        """Cache write failures must not propagate."""
        mock_client = MagicMock()
        mock_client.table.side_effect = RuntimeError("network down")
        with patch.object(query_cache, "_get_client", return_value=mock_client):
            # Should not raise
            set_cached_response("key", "q", {"answer": "..."})
