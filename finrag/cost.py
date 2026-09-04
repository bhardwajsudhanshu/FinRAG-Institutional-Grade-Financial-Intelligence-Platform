"""Cost tracking for LLM and embedding calls.

Every call to an embedder or generator should go through `record_call` so
the cost log (`data/runtime_costs.jsonl`) is always accurate. This becomes
the $/query column in `results/experiments.csv`.

Pricing (per 1M tokens, USD) — as of 2026-09, current Vertex AI public pricing:
- text-embedding-005: $0.025
- gemini-2.5-flash input: $0.075, output: $0.30
- gemini-2.5-pro input: $1.25, output: $5.00

These can be updated in `_PRICING` as Google changes them.
"""

from __future__ import annotations

import json
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from loguru import logger

from finrag.config import get_settings

_PRICING: dict[tuple[str, str], float] = {
    # (model, direction) -> USD per 1M tokens
    ("text-embedding-005", "input"): 0.025,
    ("text-embedding-004", "input"): 0.025,
    ("gemini-2.5-flash", "input"): 0.075,
    ("gemini-2.5-flash", "output"): 0.30,
    ("gemini-2.5-pro", "input"): 1.25,
    ("gemini-2.5-pro", "output"): 5.00,
    # Mock backends are free
    ("mock-embedder", "input"): 0.0,
    ("mock-generator", "input"): 0.0,
    ("mock-generator", "output"): 0.0,
}


def compute_cost_usd(model: str, input_tokens: int = 0, output_tokens: int = 0) -> float:
    """Return USD cost for a single call. Free for mock backends."""
    in_rate = _PRICING.get((model, "input"), 0.0)
    out_rate = _PRICING.get((model, "output"), 0.0)
    return (input_tokens / 1_000_000) * in_rate + (output_tokens / 1_000_000) * out_rate


def _append_log(path: Path, record: dict[str, Any]) -> None:
    """Append one JSONL record to the cost log. Atomic via append-mode write."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")


@contextmanager
def record_call(
    operation: str,
    model: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    extra: dict[str, Any] | None = None,
) -> Iterator[dict[str, Any]]:
    """Context manager that times a call, computes cost, and appends to the log.

    Usage:
        with record_call("embed", "text-embedding-005", input_tokens=128) as r:
            embedding = embedder.embed(text)
        # r["cost_usd"], r["latency_ms"] populated after exit
    """
    settings = get_settings()
    record: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "operation": operation,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": 0.0,
        "latency_ms": 0,
        "extra": extra or {},
    }
    t0 = time.perf_counter()
    try:
        yield record
    finally:
        record["latency_ms"] = int((time.perf_counter() - t0) * 1000)
        record["cost_usd"] = compute_cost_usd(model, input_tokens, output_tokens)
        try:
            _append_log(Path(settings.cost_log_path), record)
        except OSError as e:
            logger.warning(f"Could not write cost log: {e}")


def daily_cost_summary() -> dict[str, Any]:
    """Summarize today's costs by model. Used in cost dashboards."""
    settings = get_settings()
    path = Path(settings.cost_log_path)
    if not path.exists():
        return {"total_usd": 0.0, "by_model": {}, "call_count": 0}
    today = datetime.now(timezone.utc).date().isoformat()
    total = 0.0
    by_model: dict[str, float] = {}
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if r.get("ts", "").startswith(today):
            total += r.get("cost_usd", 0.0)
            m = r.get("model", "unknown")
            by_model[m] = by_model.get(m, 0.0) + r.get("cost_usd", 0.0)
            count += 1
    return {"total_usd": total, "by_model": by_model, "call_count": count}
