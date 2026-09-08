"""Pre-warm the serving Qdrant collection (STEP_037).

Embeds the eval corpus once and upserts with recreate=True. Afterwards,
serve with QDRANT_RECREATE=false to attach without re-embedding:

    CHUNKER_STRATEGY=naive VECTORDB_BACKEND=qdrant uv run python scripts/build_serve_index.py
    CHUNKER_STRATEGY=naive RETRIEVAL_STRATEGY=hybrid VECTORDB_BACKEND=qdrant QDRANT_RECREATE=false make serve
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from finrag.config import get_settings
from finrag.eval.ragas_runner import build_index_for_qa_pairs


def main() -> int:
    settings = get_settings()
    if settings.vectordb_backend != "qdrant":
        print("[FAIL] set VECTORDB_BACKEND=qdrant for pre-warming", file=sys.stderr)
        return 2
    t0 = time.perf_counter()
    bundle, _, _ = build_index_for_qa_pairs(Path("data/eval/qa_pairs.jsonl"))
    n = bundle["n_chunks"]
    print(f"[OK] warmed {settings.qdrant_collection!r}: {n} chunks "
          f"in {time.perf_counter() - t0:.0f}s (recreate={settings.qdrant_recreate})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
