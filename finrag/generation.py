"""Pluggable generator interface with two backends:

- `MockGenerator`: deterministic templated answers. Used to validate the
  retrieval pipeline without burning LLM tokens. Always returns the top-K
  retrieved chunks as a bulleted list with citations.
- `VertexGenerator`: real Gemini via Vertex AI. Stub for now.

The system prompt enforces a strict "cite your sources" format. Every backend
must return both the answer text and a list of citation metadata.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from loguru import logger

from finrag.config import get_settings
from finrag.cost import record_call


# System prompt shared by all backends. This is the contract that makes
# answers auditable. Don't change it without re-running RAGAS.
SYSTEM_PROMPT = """You are a financial analyst answering questions about SEC filings.
Use ONLY the context provided below. Every claim must cite its source by
[chunk_id]. If the context does not contain the answer, say "I cannot find
this in the provided filings." Do not invent numbers, dates, or companies.

Format your response as:
- A direct answer (1-3 sentences)
- A "Sources:" section listing the [chunk_id]s you used
"""


@dataclass
class Citation:
    """A single source citation in a generated answer."""

    chunk_id: str
    score: float  # retrieval score (cosine, BM25, RRF, etc.)
    metadata: dict = field(default_factory=dict)


@dataclass
class GenerationResult:
    """The output of a generation call, with citations attached."""

    answer: str
    citations: list[Citation]
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    model: str = ""


class BaseGenerator(ABC):
    @property
    @abstractmethod
    def model_id(self) -> str: ...

    @abstractmethod
    def generate(self, question: str, contexts: list[tuple[str, Citation]]) -> GenerationResult: ...


class MockGenerator(BaseGenerator):
    """No-LLM generator. Returns a templated answer from the retrieved chunks.

    Useful for:
    - Verifying the retrieval pipeline end-to-end (does the right chunk get retrieved?)
    - CI tests (no API flakiness)
    - Day-1 development before GCP is wired
    """

    @property
    def model_id(self) -> str:
        return "mock-generator"

    def generate(self, question: str, contexts: list[tuple[str, Citation]]) -> GenerationResult:
        # Estimate tokens: 1 token ~= 4 chars
        ctx_text = "\n\n".join(t for t, _ in contexts)
        in_tok = max(1, (len(question) + len(ctx_text) + len(SYSTEM_PROMPT)) // 4)
        out_text = self._compose(question, contexts)
        out_tok = max(1, len(out_text) // 4)
        # Log the call (cost is 0.0 for mocks but we want the latency + token counts)
        with record_call("generate", self.model_id, input_tokens=in_tok, output_tokens=out_tok) as rec:
            # No actual work; the context manager captures wall-clock time
            pass
        return GenerationResult(
            answer=out_text,
            citations=[c for _, c in contexts],
            input_tokens=in_tok,
            output_tokens=out_tok,
            cost_usd=rec.get("cost_usd", 0.0),
            model=self.model_id,
        )

    def _compose(self, question: str, contexts: list[tuple[str, Citation]]) -> str:
        if not contexts:
            return (
                "I cannot find this in the provided filings.\n\n"
                "Sources: (none retrieved)"
            )
        # Take the first 240 chars of the top chunk as the "answer"
        top_text, top_cite = contexts[0]
        snippet = top_text.strip().replace("\n", " ")[:240]
        if len(top_text.strip()) > 240:
            snippet += "..."
        sources = "\n".join(f"- [{c.chunk_id}] (score={c.score:.3f})" for _, c in contexts)
        return (
            f"Based on the retrieved filings: {snippet}\n\n"
            f"Sources:\n{sources}"
        )


class VertexGenerator(BaseGenerator):
    """Real Gemini generator via Vertex AI. Stub for now — wire when ready."""

    def __init__(self, model_id: str, project_id: str, region: str):
        self._model_id = model_id
        self._project_id = project_id
        self._region = region
        import vertexai  # type: ignore
        from vertexai.generative_models import GenerativeModel  # type: ignore

        # CRITICAL: vertexai.init must run before any model call so the SDK
        # uses the service-account creds, not ADC fallback (gcloud user creds,
        # which have no quota project and return 403 SERVICE_DISABLED).
        vertexai.init(project=project_id, location=region)
        # Service-account creds don't carry a quota project; set it explicitly.
        import os
        os.environ.setdefault("GOOGLE_CLOUD_QUOTA_PROJECT", project_id)
        self._client = GenerativeModel(model_id)

    @property
    def model_id(self) -> str:
        return self._model_id

    def generate(self, question: str, contexts: list[tuple[str, Citation]]) -> GenerationResult:
        ctx_text = "\n\n---\n\n".join(
            f"[{c.chunk_id}]\n{t}" for t, c in contexts
        )
        prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"Context:\n{ctx_text}\n\n"
            f"Question: {question}\n\n"
            f"Answer:"
        )
        in_tok = 0
        out_tok = 0
        with record_call("generate", self._model_id) as rec:
            response = self._client.generate_content(prompt)
            # Update the record IN-PLACE before the context manager exits,
            # so the cost log line written on exit reflects real usage.
            usage = getattr(response, "usage_metadata", None)
            if usage is not None:
                in_tok = int(getattr(usage, "prompt_token_count", 0) or 0)
                out_tok = int(getattr(usage, "candidates_token_count", 0) or 0)
                rec["input_tokens"] = in_tok
                rec["output_tokens"] = out_tok
        return GenerationResult(
            answer=response.text,
            citations=[c for _, c in contexts],
            input_tokens=in_tok,
            output_tokens=out_tok,
            cost_usd=rec.get("cost_usd", 0.0),
            model=self._model_id,
        )


def get_generator() -> BaseGenerator:
    settings = get_settings()
    if settings.generator_backend == "mock":
        return MockGenerator()
    if settings.generator_backend == "vertex":
        if not settings.gcp_project_id:
            raise RuntimeError(
                "GENERATOR_BACKEND=vertex but GCP_PROJECT_ID is empty. "
                "Either set it in .env or set GENERATOR_BACKEND=mock."
            )
        return VertexGenerator(
            model_id=settings.vertex_generator_model,
            project_id=settings.gcp_project_id,
            region=settings.gcp_region,
        )
    raise ValueError(f"Unknown generator backend: {settings.generator_backend!r}")
