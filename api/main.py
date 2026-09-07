"""FinRAG FastAPI service — the sweep winner behind HTTP (STEP_020).

Endpoints:
- GET  /health      — liveness + index stats (no model calls)
- POST /ask         — retrieve -> generate a cited answer
- GET  /leaderboard — the frozen experiment leaderboard JSON

Run:
    CHUNKER_STRATEGY=naive RETRIEVAL_STRATEGY=hybrid uv run uvicorn api.main:app --port 8000
    # + VECTORDB_BACKEND=qdrant (needs `make docker-up`) for the live store

Design notes:
- `create_app()` with no args defers ALL heavy work to lifespan (import
  is instant; startup builds the corpus once). Tests inject a prebuilt
  bundle + generator instead and never touch the network.
- Retrieval/generation go through the same functions as the eval runner
  (`retrieve_with_strategy`, `BaseGenerator.generate`), so served answers
  match benchmarked behavior by construction.
- Errors from retrieval/generation surface as 500s with the message only
  (no tracebacks to clients); validation failures are 422s via pydantic.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

from finrag.config import get_settings


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    # Best-answer mode (STEP_026): re-rank top-10 with Flash pointwise and
    # generate from the top-`top_k`. Slower (~30s) and bills scoring calls;
    # default off (hybrid order, free).
    rerank: bool = False


class CitationOut(BaseModel):
    chunk_id: str
    score: float
    ticker: str = ""
    section_id: str = ""


class AskResponse(BaseModel):
    answer: str
    citations: list[CitationOut]
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: int
    retrieval_strategy: str
    vectordb_backend: str
    reranked: bool = False


class HealthResponse(BaseModel):
    status: str
    n_chunks: int
    chunker_strategy: str
    retrieval_strategy: str
    vectordb_backend: str
    generator_model: str


def create_app(bundle: dict | None = None, generator: Any | None = None,
               chunk_id_to_text: dict | None = None,
               reranker: Any | None = None) -> FastAPI:
    """Build the app. Prebuilt args (tests) skip the lifespan index build.

    `reranker` (tests) overrides the best-answer scorer; production builds
    a Flash pointwise reranker on first `rerank=true` request (needs GCP).
    """
    app = FastAPI(title="FinRAG", version="0.1.0")
    app.state.bundle = bundle
    app.state.generator = generator
    app.state.chunk_id_to_text = chunk_id_to_text or {}
    app.state.reranker = reranker
    app.state.meta = {"chunker_strategy": get_settings().chunker_strategy}

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if app.state.bundle is None:
            from finrag.eval.ragas_runner import build_index_for_qa_pairs
            from finrag.generation import get_generator

            settings = get_settings()
            logger.info(
                "Serving index build: chunker={} retrieval={} vectordb={}",
                settings.chunker_strategy, settings.retrieval_strategy,
                settings.vectordb_backend,
            )
            b, _, _ = build_index_for_qa_pairs(Path("data/eval/qa_pairs.jsonl"))
            app.state.bundle = b
            app.state.generator = get_generator()
            app.state.meta = {
                "chunker_strategy": settings.chunker_strategy,
                "generator_model": app.state.generator.model_id,
            }
            logger.info("Serving index ready: {} chunks", b["n_chunks"])
        yield

    app.router.lifespan_context = lifespan

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        b = app.state.bundle
        if b is None:
            raise HTTPException(status_code=503, detail="index not built yet")
        return HealthResponse(
            status="ok",
            n_chunks=b["n_chunks"],
            chunker_strategy=app.state.meta.get("chunker_strategy", ""),
            retrieval_strategy=b["strategy"],
            vectordb_backend=b.get("vectordb_backend", "in-memory"),
            generator_model=getattr(app.state.generator, "model_id", ""),
        )

    @app.post("/ask", response_model=AskResponse)
    def ask(req: AskRequest) -> AskResponse:
        import time

        from finrag.retrieval import results_to_citations, retrieve_with_strategy

        b = app.state.bundle
        if b is None or app.state.generator is None:
            raise HTTPException(status_code=503, detail="index not built yet")
        question = req.question.strip()
        if not question:
            raise HTTPException(status_code=422, detail="question must not be blank")
        t0 = time.perf_counter()
        reranked = False
        try:
            if req.rerank:
                from finrag.rerank import FlashPointwiseReranker

                fetch_k = max(req.top_k, 10)
                retrieved = retrieve_with_strategy(b, question, top_k=fetch_k)
                rr = app.state.reranker
                if rr is None:
                    settings = get_settings()
                    rr = FlashPointwiseReranker(
                        project_id=settings.gcp_project_id,
                        region=settings.gcp_region)
                retrieved = rr.rerank(question, retrieved, req.top_k)
                reranked = True
            else:
                retrieved = retrieve_with_strategy(b, question, top_k=req.top_k)
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"ask retrieval failed: {e}")
            raise HTTPException(status_code=500, detail=f"retrieval failed: {e}") from e
        cites = results_to_citations(retrieved)
        contexts = [(c.text, cites[i]) for i, (c, _s) in enumerate(retrieved)]
        try:
            gen = app.state.generator.generate(question, contexts)
        except Exception as e:
            logger.warning(f"ask generation failed: {e}")
            raise HTTPException(status_code=500, detail=f"generation failed: {e}") from e
        return AskResponse(
            answer=gen.answer,
            citations=[CitationOut(chunk_id=c.chunk_id, score=c.score,
                                   ticker=str(c.metadata.get("ticker", "")),
                                   section_id=str(c.metadata.get("section_id", "")))
                       for c in gen.citations],
            model=gen.model,
            input_tokens=gen.input_tokens,
            output_tokens=gen.output_tokens,
            cost_usd=gen.cost_usd,
            latency_ms=int((time.perf_counter() - t0) * 1000),
            retrieval_strategy=b["strategy"],
            vectordb_backend=b.get("vectordb_backend", "in-memory"),
            reranked=reranked,
        )

    @app.get("/leaderboard")
    def leaderboard() -> dict[str, Any]:
        import json

        path = get_settings().project_root / "results" / "leaderboard.json"
        if not path.exists():
            raise HTTPException(status_code=404, detail="leaderboard not built yet")
        return json.loads(path.read_text(encoding="utf-8"))

    return app


app = create_app()
