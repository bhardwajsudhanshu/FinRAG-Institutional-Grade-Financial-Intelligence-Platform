"""Pluggable embedder interface with two backends:

- `MockEmbedder`: deterministic, hash-based. Same input -> same vector, every time.
  Zero network calls. Used for offline development and the smoke test.
- `VertexEmbedder`: real `text-embedding-005` via Vertex AI. Wires up when
  EMBEDDER_BACKEND=vertex and GCP_PROJECT_ID is set.

Selection is by config (`finrag.config.settings.embedder_backend`).
"""

from __future__ import annotations

import hashlib
import math
from abc import ABC, abstractmethod

from loguru import logger

from finrag.config import get_settings
from finrag.cost import record_call


class BaseEmbedder(ABC):
    """Abstract embedder. All backends implement this interface."""

    @property
    @abstractmethod
    def dim(self) -> int:
        """Embedding dimensionality."""

    @property
    @abstractmethod
    def model_id(self) -> str:
        """Identifier used in cost logs and experiment configs."""

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Embed a single text. Returns a list of floats of length `dim`."""

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Default: sequential single calls. Override for batch-optimized backends."""
        return [self.embed(t) for t in texts]


class MockEmbedder(BaseEmbedder):
    """Deterministic hash-based embedder. Useful for offline development.

    Properties:
    - Same input text -> same vector (so retrieval is reproducible)
    - Dimension matches settings.embedding_dim (default 768)
    - Vectors are L2-normalized, so cosine similarity is a real dot product
    - Zero cost, zero network, zero rate limits

    Limitations:
    - Not semantically meaningful. Two unrelated sentences will have ~0 similarity
      but two very similar sentences (shared n-grams) will have non-zero.
      Good enough to validate the pipeline end-to-end.
    """

    def __init__(self, dim: int):
        self._dim = dim

    @property
    def dim(self) -> int:
        return self._dim

    @property
    def model_id(self) -> str:
        return "mock-embedder"

    def embed(self, text: str) -> list[float]:
        # Tokenize lightly on whitespace + lowercase
        tokens = text.lower().split()
        # Build a sparse feature vector from token hashes (feature hashing)
        vec = [0.0] * self._dim
        for tok in tokens:
            h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
            idx = h % self._dim
            sign = 1.0 if (h // self._dim) % 2 == 0 else -1.0
            vec[idx] += sign
        # Sublinear TF: log normalize
        for i in range(self._dim):
            vec[i] = math.copysign(math.log1p(abs(vec[i])), vec[i])
        # L2 normalize
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]


class VertexEmbedder(BaseEmbedder):
    """Real Vertex AI embedder. Stub for now — wire when ready."""

    def __init__(self, model_id: str, project_id: str, region: str):
        self._model_id = model_id
        self._project_id = project_id
        self._region = region
        # Lazy import so mock-only installs don't require google-cloud-aiplatform
        from vertexai.language_models import TextEmbeddingModel  # type: ignore

        self._client = TextEmbeddingModel.from_pretrained(model_id)

    @property
    def dim(self) -> int:
        # text-embedding-005/004 are 768-dim
        return 768

    @property
    def model_id(self) -> str:
        return self._model_id

    def embed(self, text: str) -> list[float]:
        embeddings = self._client.get_embeddings([text])
        return list(embeddings[0].values)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        # Vertex supports batch embedding in a single API call
        # Approximate tokens for cost estimation (1 token ~= 4 chars for English)
        total_chars = sum(len(t) for t in texts)
        est_tokens = max(1, total_chars // 4)
        with record_call("embed_batch", self._model_id, input_tokens=est_tokens) as rec:
            embeddings = self._client.get_embeddings(texts)
        rec["batch_size"] = len(texts)
        return [list(e.values) for e in embeddings]


def get_embedder() -> BaseEmbedder:
    """Factory: return the configured embedder backend."""
    settings = get_settings()
    if settings.embedder_backend == "mock":
        return MockEmbedder(dim=settings.embedding_dim)
    if settings.embedder_backend == "vertex":
        if not settings.gcp_project_id:
            raise RuntimeError(
                "EMBEDDER_BACKEND=vertex but GCP_PROJECT_ID is empty. "
                "Either set it in .env or set EMBEDDER_BACKEND=mock."
            )
        return VertexEmbedder(
            model_id=settings.vertex_embedding_model,
            project_id=settings.gcp_project_id,
            region=settings.gcp_region,
        )
    raise ValueError(f"Unknown embedder backend: {settings.embedder_backend!r}")
