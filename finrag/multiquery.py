"""Multi-query retrieval expansion (STEP_034, exp_043).

Pattern: ask the LLM for N paraphrases of the question, retrieve once per
formulation (original + paraphrases) with the configured strategy, RRF-fuse
all rankings, keep top-K. Helps vocabulary-mismatch Q's (user words differ
from filing words); costs one Flash call + N extra retrievals per Q.

- `expand_query(question, n, generate_fn)`: paraphrases via injected fn
  (tests) or Flash JSON mode (production).
- `multi_query_retrieve(bundle, question, top_k, ...)`: orchestration over
  `retrieve_with_strategy` — works over ANY base strategy (dense, hybrid,
  parent-doc...), which is why it is a flag, not a strategy.
"""

from __future__ import annotations

from collections.abc import Callable

from loguru import logger

from finrag.chunking import Chunk
from finrag.config import get_settings
from finrag.cost import record_call
from finrag.retrieval import reciprocal_rank_fusion, retrieve_with_strategy

_EXPAND_PROMPT = """Generate {n} diverse paraphrases of the financial question below.
Vary the wording (synonyms, question forms) but preserve the exact meaning
and every number, ticker, date, and section reference.

Respond with JSON only: {{"paraphrases": ["...", ...]}}

Question: {question}
"""


class QueryExpander:
    """Flash paraphraser. `generate_fn` injectable for offline tests."""

    def __init__(self, model_id: str = "gemini-2.5-flash",
                 project_id: str = "", region: str = "us-central1",
                 generate_fn: Callable[[str, int], list[str]] | None = None) -> None:
        self._model_id = model_id
        self._generate_fn = generate_fn or self._vertex_expand
        if generate_fn is None:
            if not project_id:
                raise RuntimeError(
                    "QueryExpander needs GCP_PROJECT_ID "
                    "(or pass generate_fn for offline use)."
                )
            import vertexai  # type: ignore
            from vertexai.generative_models import GenerativeModel  # type: ignore

            vertexai.init(project=project_id, location=region)
            import os
            os.environ.setdefault("GOOGLE_CLOUD_QUOTA_PROJECT", project_id)
            self._client = GenerativeModel(
                model_id,
                generation_config={"response_mime_type": "application/json",
                                   "temperature": 0.7},
            )
        else:
            self._client = None

    def expand(self, question: str, n: int = 3) -> list[str]:
        """Return up to n paraphrases (fewer on failure — never raises)."""
        try:
            out = self._generate_fn(question, n)
            return [p.strip() for p in (out or []) if p and p.strip()][:n]
        except Exception as e:
            logger.warning(f"query expansion failed, single-query fallback: {e}")
            return []

    def _vertex_expand(self, question: str, n: int) -> list[str]:
        import json

        prompt = _EXPAND_PROMPT.format(n=n, question=question)
        with record_call("multiquery_expand", self._model_id) as rec:
            response = self._client.generate_content(prompt)
            usage = getattr(response, "usage_metadata", None)
            if usage is not None:
                rec["input_tokens"] = int(getattr(usage, "prompt_token_count", 0) or 0)
                rec["output_tokens"] = int(getattr(usage, "candidates_token_count", 0) or 0)
        data = json.loads(response.text)
        paras = data.get("paraphrases", [])
        if not isinstance(paras, list):
            raise ValueError("paraphrases is not a list")
        return [str(p) for p in paras]


def get_expander() -> QueryExpander:
    """Factory (settings only matter when expansion is enabled)."""
    settings = get_settings()
    return QueryExpander(project_id=settings.gcp_project_id,
                         region=settings.gcp_region)


def multi_query_retrieve(bundle: dict, question: str, top_k: int = 5,
                         paraphrases: list[str] | None = None,
                         per_query_k: int | None = None,
                         rrf_k: int = 60) -> list[tuple[Chunk, float]]:
    """Retrieve once per formulation, RRF-fuse, truncate to top_k.

    Fusion happens over the FINAL per-query rankings (whatever the base
    strategy returns — dense chunks, BM25 chunks, or mapped parents), so
    this composes with every strategy without knowing their internals.
    Empty paraphrases == single-query behavior exactly. Scores are RRF
    fused scores (rank space, like hybrid); ties resolve deterministically
    (fused score desc, then first-appearance order with the original query
    first, then chunk id).
    """
    queries = [question, *list(paraphrases or [])]
    k = per_query_k or top_k
    ranked: list[list[str]] = []
    objs: dict[str, Chunk] = {}
    for q in queries:
        hits = retrieve_with_strategy(bundle, q, top_k=k)
        ranked.append([c.chunk_id for c, _ in hits])
        for c, _ in hits:
            objs.setdefault(c.chunk_id, c)
    fused = reciprocal_rank_fusion(ranked, rrf_k=rrf_k)
    order = {cid: i for i, lst in enumerate(ranked) for cid in lst}
    fused.sort(key=lambda kv: (-kv[1], order.get(kv[0], len(ranked)), kv[0]))
    return [(objs[cid], score) for cid, score in fused[:top_k] if cid in objs]
