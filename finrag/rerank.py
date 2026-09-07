"""Post-retrieval re-ranking (Phase 5, ADR-006, exp_030).

Pipeline position: retrieve top-N (N=`rerank_candidates`) -> score each
(question, chunk) -> keep top-K by score. Goal: close the
recall-vs-citation gap (right chunks retrieved but not ranked first).

Scorers:
- `NoopReranker`: identity (default; all frozen rows; also the offline test double).
- `FlashPointwiseReranker`: `gemini-2.5-flash` scores 0-10 in JSON mode.
  `score_fn` is injectable so unit tests never call Vertex.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable

from loguru import logger

from finrag.chunking import Chunk
from finrag.config import get_settings
from finrag.cost import record_call


class BaseReranker(ABC):
    @abstractmethod
    def rerank(self, question: str, items: list[tuple[Chunk, float]],
               top_k: int = 5) -> list[tuple[Chunk, float]]:
        """Re-order items, return top_k. Output scores stay on the input
        (retrieval) scale — reranking only reorders, never rescores."""


class NoopReranker(BaseReranker):
    """Identity: first top_k unchanged. Default; keeps frozen rows frozen."""

    def rerank(self, question: str, items: list[tuple[Chunk, float]],
               top_k: int = 5) -> list[tuple[Chunk, float]]:
        return list(items[:top_k])


_SCORE_PROMPT = """Rate how relevant this filing excerpt is for answering the question.
Respond with JSON only: {{"score": <integer 0-10>}}.
0 = unrelated. 10 = directly contains the answer.

Question: {question}

Excerpt:
\"\"\"
{chunk_text}
\"\"\"
"""


class FlashPointwiseReranker(BaseReranker):
    """Pointwise Flash scorer (ADR-006). One JSON call per candidate.

    Unscorable chunks (parse failure after retries) sink below scored
    ones with original relative order kept (stable sort) — retrieval
    order is the tie-break everywhere, so runs stay reproducible.
    """

    def __init__(self, model_id: str = "gemini-2.5-flash",
                 project_id: str = "", region: str = "us-central1",
                 score_fn: Callable[[str, str], float | None] | None = None) -> None:
        self._model_id = model_id
        self._score_fn = score_fn or self._vertex_score
        if score_fn is None:
            if not project_id:
                raise RuntimeError(
                    "FlashPointwiseReranker needs GCP_PROJECT_ID "
                    "(or pass score_fn for offline use)."
                )
            import vertexai  # type: ignore
            from vertexai.generative_models import GenerativeModel  # type: ignore

            vertexai.init(project=project_id, location=region)
            import os
            os.environ.setdefault("GOOGLE_CLOUD_QUOTA_PROJECT", project_id)
            self._client = GenerativeModel(
                model_id,
                generation_config={"response_mime_type": "application/json",
                                   "temperature": 0.0},
            )
        else:
            self._client = None

    @property
    def model_id(self) -> str:
        return f"{self._model_id}-pointwise-rerank"

    def _vertex_score(self, question: str, chunk_text: str) -> float | None:
        import json

        prompt = _SCORE_PROMPT.format(question=question, chunk_text=chunk_text[:4000])
        for attempt in range(3):
            try:
                with record_call("rerank", self._model_id) as rec:
                    response = self._client.generate_content(
                        prompt + ("\nREMINDER: JSON only." if attempt else ""))
                    usage = getattr(response, "usage_metadata", None)
                    if usage is not None:
                        rec["input_tokens"] = int(getattr(usage, "prompt_token_count", 0) or 0)
                        rec["output_tokens"] = int(getattr(usage, "candidates_token_count", 0) or 0)
                score = int(json.loads(response.text)["score"])
                return max(0.0, min(10.0, float(score)))
            except Exception as e:
                logger.warning(f"rerank score parse failed (attempt {attempt + 1}): {e}")
        return None

    def rerank(self, question: str, items: list[tuple[Chunk, float]],
               top_k: int = 5) -> list[tuple[Chunk, float]]:
        scored: list[tuple[float | None, float, int, Chunk]] = []
        for rank, (chunk, ret_score) in enumerate(items):
            try:
                s = self._score_fn(question, chunk.text)
            except Exception as e:
                logger.warning(f"rerank scorer failed, chunk sinks: {e}")
                s = None
            scored.append((s, ret_score, rank, chunk))
        # Scored first (score desc), then unscored in retrieval order;
        # retrieval score, then original rank, break all ties deterministically.
        # Output keeps retrieval-scale scores: rerank reorders only.
        scored.sort(key=lambda t: (t[0] is not None, t[0] or 0.0, t[1], -t[2]),
                    reverse=True)
        return [(c, r) for _, r, _, c in scored[:top_k]]


def get_reranker() -> BaseReranker:
    """Factory from settings (`rerank_backend`: none | flash-pointwise)."""
    settings = get_settings()
    if settings.rerank_backend == "none":
        return NoopReranker()
    if settings.rerank_backend == "flash-pointwise":
        return FlashPointwiseReranker(
            project_id=settings.gcp_project_id, region=settings.gcp_region)
    raise ValueError(
        f"Unknown rerank backend: {settings.rerank_backend!r}. "
        "Valid options: ['none', 'flash-pointwise']"
    )
