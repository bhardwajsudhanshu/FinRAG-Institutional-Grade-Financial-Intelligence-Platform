"""UI helper tests (STEP_021). Offline: httpx is stubbed, no API needed."""

from __future__ import annotations

import sys
from pathlib import Path

# tests/ -> project root
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import httpx

from ui.streamlit_app import api_url, fetch_health, fetch_leaderboard_winners, query_api


class _Resp:
    def __init__(self, status_code: int, payload: dict | str = "") -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = payload if isinstance(payload, str) else ""

    def json(self):
        if isinstance(self._payload, dict):
            return self._payload
        raise ValueError("no json")


class TestApiUrl:
    def test_default_localhost(self, monkeypatch) -> None:
        monkeypatch.delenv("FINRAG_API_URL", raising=False)
        assert api_url() == "http://localhost:8000"

    def test_env_override_strips_slash(self, monkeypatch) -> None:
        monkeypatch.setenv("FINRAG_API_URL", "http://gpu-box:9000/")
        assert api_url() == "http://gpu-box:9000"


class TestQueryApi:
    def test_happy_path(self, monkeypatch) -> None:
        payload = {"answer": "A", "citations": [], "model": "m",
                   "input_tokens": 1, "output_tokens": 2, "cost_usd": 0.0,
                   "latency_ms": 3, "retrieval_strategy": "hybrid",
                   "vectordb_backend": "in-memory"}
        monkeypatch.setattr(httpx, "post", lambda *a, **k: _Resp(200, payload))
        assert query_api("Revenue?", top_k=5) == payload

    def test_rerank_flag_reaches_api(self, monkeypatch) -> None:
        seen: dict = {}

        def fake_post(url, json=None, **k):
            seen.clear()
            seen.update(json or {})
            return _Resp(200, {"answer": "A", "citations": []})
        monkeypatch.setattr(httpx, "post", fake_post)
        query_api("Revenue?", top_k=5, rerank=True)
        assert seen.get("rerank") is True
        query_api("Revenue?")
        assert seen.get("rerank") is False

    def test_connection_error_is_human(self, monkeypatch) -> None:
        def boom(*a, **k):
            raise httpx.ConnectError("refused")
        monkeypatch.setattr(httpx, "post", boom)
        try:
            query_api("Revenue?")
            raise AssertionError("should have raised")
        except RuntimeError as e:
            assert "make serve" in str(e)

    def test_422_is_human(self, monkeypatch) -> None:
        monkeypatch.setattr(httpx, "post", lambda *a, **k: _Resp(422))
        try:
            query_api("")
            raise AssertionError("should have raised")
        except RuntimeError as e:
            assert "1-2000" in str(e)

    def test_500_surfaces_body(self, monkeypatch) -> None:
        monkeypatch.setattr(httpx, "post", lambda *a, **k: _Resp(500, "boom"))
        try:
            query_api("Revenue?")
            raise AssertionError("should have raised")
        except RuntimeError as e:
            assert "500" in str(e)


class TestHealth:
    def test_down_returns_none(self, monkeypatch) -> None:
        def boom(*a, **k):
            raise httpx.ConnectError("refused")
        monkeypatch.setattr(httpx, "get", boom)
        assert fetch_health() is None

    def test_up_parses(self, monkeypatch) -> None:
        monkeypatch.setattr(httpx, "get",
                            lambda *a, **k: _Resp(200, {"status": "ok", "n_chunks": 4447}))
        assert fetch_health()["n_chunks"] == 4447


class TestLeaderboard:
    def test_flattens_categories(self, monkeypatch) -> None:
        payload = {"categories": {
            "retrieval": {"winner": "exp_021", "winner_value": 0.88},
            "vectordb": {"winner": None, "winner_value": None},
        }}
        monkeypatch.setattr(httpx, "get", lambda *a, **k: _Resp(200, payload))
        rows = fetch_leaderboard_winners()
        assert ("retrieval", "exp_021", 0.88) in rows
        assert ("vectordb", None, None) in rows

    def test_down_returns_empty(self, monkeypatch) -> None:
        def boom(*a, **k):
            raise httpx.ConnectError("refused")
        monkeypatch.setattr(httpx, "get", boom)
        assert fetch_leaderboard_winners() == []
