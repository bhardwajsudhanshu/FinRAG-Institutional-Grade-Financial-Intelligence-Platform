"""Exact-match answer cache for the /ask endpoint (STEP_045).

A repeat question with identical (strategy, top_k, rerank) skips retrieval
AND generation: $0, ~0ms. Key normalization is case/whitespace folding only —
no semantic near-matching (that needs threshold tuning + eval; filed as the
auto-router follow-up, not smuggled in here).

Bounded FIFO eviction (default 512 entries) so a long-lived fleet worker
cannot grow memory without limit. Thread-safety: uvicorn workers are separate
processes (each owns its cache); within a worker, asyncio runs the endpoint
(one event loop — dict ops are atomic enough for a cache).
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any


class AnswerCache:
    """FIFO-bounded exact-match cache. Stores response objects as-is."""

    def __init__(self, maxsize: int = 512) -> None:
        if maxsize < 1:
            raise ValueError(f"maxsize must be >= 1, got {maxsize}")
        self._maxsize = maxsize
        self._data: OrderedDict[tuple, Any] = OrderedDict()
        self.hits = 0
        self.misses = 0

    @staticmethod
    def normalize(question: str) -> str:
        """Fold case + collapse whitespace. Punctuation kept (cheap, honest)."""
        return " ".join(question.strip().lower().split())

    @classmethod
    def key(cls, strategy: str, top_k: int, reranked: bool, question: str) -> tuple:
        return (strategy, top_k, reranked, cls.normalize(question))

    def get(self, strategy: str, top_k: int, reranked: bool, question: str) -> Any | None:
        key = self.key(strategy, top_k, reranked, question)
        if key in self._data:
            self.hits += 1
            return self._data[key]
        self.misses += 1
        return None

    def put(self, strategy: str, top_k: int, reranked: bool,
            question: str, response: Any) -> None:
        key = self.key(strategy, top_k, reranked, question)
        if key in self._data:
            self._data[key] = response
            return
        while len(self._data) >= self._maxsize:
            self._data.popitem(last=False)  # evict oldest
        self._data[key] = response

    def stats(self) -> dict:
        total = self.hits + self.misses
        return {"size": len(self._data), "maxsize": self._maxsize,
                "hits": self.hits, "misses": self.misses,
                "hit_rate": (self.hits / total) if total else 0.0}

    def __len__(self) -> int:
        return len(self._data)
