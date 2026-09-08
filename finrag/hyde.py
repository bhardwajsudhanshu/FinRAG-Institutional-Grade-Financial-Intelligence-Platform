"""HyDE retrieval (STEP_039, exp_044).

Pattern (Gao et al. 2022): ask the LLM to write a HYPOTHETICAL answer
passage, embed the passage instead of the (short, vague) question, and
retrieve by document-to-document similarity. Fused with the original
query's ranking (anchored HyDE) so hallucinated specifics in the
hypothetical doc can't drag retrieval fully off-course.

- `HyDEGenerator`: Flash prose passage, injectable `generate_fn` for
  offline tests. Failures return "" (caller falls back to direct).
- `hyde_retrieve(bundle, question, top_k, hyde_text)`: run the hyde prose
  through the SAME dispatcher as a second query, RRF-fuse both rankings,
  truncate. Composes with every base strategy (dense, hybrid, parent-doc)
  with no special cases.
"""

from __future__ import annotations

from collections.abc import Callable

from loguru import logger

from finrag.chunking import Chunk
from finrag.config import get_settings
from finrag.cost import record_call
from finrag.retrieval import reciprocal_rank_fusion

_HYDE_PROMPT = """Write a short hypothetical excerpt from a company's SEC 10-K filing that would directly answer the question below. Write it in authentic 10-K language (formal, numerical, specific) even if you must invent plausible figures — this text is only used for similarity search, never shown to users.

Question: {question}

Excerpt (3-6 sentences):"""


class HyDEGenerator:
    """Flash hypothetical-document writer. `generate_fn` injectable."""

    def __init__(self, model_id: str = "gemini-2.5-flash",
                 project_id: str = "", region: str = "us-central1",
                 generate_fn: Callable[[str], str] | None = None) -> None:
        self._model_id = model_id
        self._generate_fn = generate_fn or self._vertex_write
        if generate_fn is None:
            if not project_id:
                raise RuntimeError(
                    "HyDEGenerator needs GCP_PROJECT_ID "
                    "(or pass generate_fn for offline use)."
                )
            import vertexai  # type: ignore
            from vertexai.generative_models import GenerativeModel  # type: ignore

            vertexai.init(project=project_id, location=region)
            import os
            os.environ.setdefault("GOOGLE_CLOUD_QUOTA_PROJECT", project_id)
            self._client = GenerativeModel(
                model_id,
                generation_config={"temperature": 0.5},
            )
        else:
            self._client = None

    def write(self, question: str) -> str:
        """Return the hypothetical passage ("" on any failure — the caller
        falls back to direct retrieval, never voids the Q)."""
        try:
            out = self._generate_fn(question)
            return out.strip() if out else ""
        except Exception as e:
            logger.warning(f"HyDE generation failed, direct fallback: {e}")
            return ""

    def _vertex_write(self, question: str) -> str:
        prompt = _HYDE_PROMPT.format(question=question)
        with record_call("hyde_write", self._model_id) as rec:
            response = self._client.generate_content(prompt)
            usage = getattr(response, "usage_metadata", None)
            if usage is not None:
                rec["input_tokens"] = int(getattr(usage, "prompt_token_count", 0) or 0)
                rec["output_tokens"] = int(getattr(usage, "candidates_token_count", 0) or 0)
        from finrag.generation import _response_text

        return _response_text(response)


def get_hyde_generator() -> HyDEGenerator:
    """Factory (settings only matter when HyDE is enabled)."""
    settings = get_settings()
    return HyDEGenerator(project_id=settings.gcp_project_id,
                         region=settings.gcp_region)


def hyde_fuse(bundle: dict, question: str, top_k: int = 5,
              hyde_text: str = "", base_hits: list | None = None,
              rrf_k: int = 60) -> list[tuple[Chunk, float]]:
    """RRF-fuse a base ranking with the hyde-doc ranking.

    `base_hits` (already-retrieved top-K, e.g. multiquery-fused) avoids
    re-running the base path; None falls back to direct retrieval.
    The hyde side always runs through `retrieve_with_strategy`, so this
    composes with every base strategy. Empty `hyde_text` returns base
    unchanged. Deterministic tie-breaks (fused desc, then base-first
    appearance, then chunk id).
    """
    from finrag.retrieval import retrieve_with_strategy

    if base_hits is None:
        base_hits = retrieve_with_strategy(bundle, question, top_k=top_k)
    if not hyde_text.strip():
        return list(base_hits)
    hyde_hits = retrieve_with_strategy(bundle, hyde_text, top_k=top_k)
    ranked = [[c.chunk_id for c, _ in base_hits],
              [c.chunk_id for c, _ in hyde_hits]]
    fused = reciprocal_rank_fusion(ranked, rrf_k=rrf_k)
    objs: dict[str, Chunk] = {}
    for c, _ in list(base_hits) + list(hyde_hits):
        objs.setdefault(c.chunk_id, c)
    order = {cid: i for i, lst in enumerate(ranked) for cid in lst}
    fused.sort(key=lambda kv: (-kv[1], order.get(kv[0], len(ranked)), kv[0]))
    return [(objs[cid], score) for cid, score in fused[:top_k] if cid in objs]


def hyde_retrieve(bundle: dict, question: str, top_k: int = 5,
                  hyde_text: str = "", rrf_k: int = 60) -> list[tuple[Chunk, float]]:
    """Anchored HyDE without a precomputed base (fuses direct + hyde)."""
    return hyde_fuse(bundle, question, top_k=top_k, hyde_text=hyde_text,
                     base_hits=None, rrf_k=rrf_k)
