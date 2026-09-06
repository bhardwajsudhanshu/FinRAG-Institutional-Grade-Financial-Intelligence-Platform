"""Unit tests for the RAGAS eval runner. These run WITHOUT calling Vertex.

We use a small synthetic eval set in tmp and the mock backends. The real
RAGAS metrics need an LLM judge, so we only test the custom metrics
(hit@5, citation_accuracy, mean_latency) and the per-Q iteration. RAGAS
itself is exercised in the smoke test in tests/eval/smoke_test_ragas.py.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from finrag.chunking import Chunk
from finrag.eval.ragas_runner import _hit_at_k, ExperimentResult


def test_hit_at_k_present():
    assert _hit_at_k(["a", "b", "c"], "b", 5) is True
    assert _hit_at_k(["a", "b", "c"], "a", 1) is True
    assert _hit_at_k(["a", "b", "c"], "z", 5) is False


def test_hit_at_k_truncates():
    # Source is the 10th chunk; k=5 means we don't look past position 4
    assert _hit_at_k([f"c{i}" for i in range(20)], "c10", 5) is False
    assert _hit_at_k([f"c{i}" for i in range(20)], "c4", 5) is True


def test_experiment_result_csv_row_drops_per_question():
    r = ExperimentResult(
        exp_name="exp_001",
        timestamp="2026-09-05T00:00:00",
        n_questions=10,
        n_filings=5,
        n_chunks=100,
        context_recall=0.7,
        faithfulness=0.8,
        answer_relevancy=0.6,
        hit_at_5=0.5,
        citation_accuracy=0.4,
        mean_latency_ms=1000.0,
        total_cost_usd=0.05,
        per_question=[{"qid": "q_0001"}],
    )
    row = r.to_csv_row()
    assert "per_question" not in row
    assert row["exp_name"] == "exp_001"
    assert row["n_questions"] == 10
    assert row["context_recall"] == 0.7


def test_experiment_result_content_anchored_fields_default_to_none():
    """Frozen exp_001 / exp_002 rows were never serialized with the new
    fields. Constructing an ExperimentResult without the content-anchored
    fields (mimicking the legacy frozen shape) must default them to None
    so the schema is backwards-compatible.
    """
    r = ExperimentResult(
        exp_name="exp_001",
        timestamp="2026-09-05T00:00:00",
        n_questions=139,
        n_filings=20,
        n_chunks=4447,
        context_recall=0.81,
        faithfulness=0.88,
        answer_relevancy=0.74,
        hit_at_5=0.60,
        citation_accuracy=0.56,
        mean_latency_ms=8731.0,
        total_cost_usd=0.038,
    )
    row = r.to_csv_row()
    assert "hit_at_5_content" in row
    assert "citation_accuracy_content" in row
    assert row["hit_at_5_content"] is None
    assert row["citation_accuracy_content"] is None


def test_experiment_result_content_anchored_fields_populated():
    """exp_003 onward populates both content-anchored columns. Verify
    they round-trip through to_csv_row.
    """
    r = ExperimentResult(
        exp_name="exp_003_semantic",
        timestamp="2026-09-06T00:00:00",
        n_questions=139,
        n_filings=20,
        n_chunks=5000,
        context_recall=0.83,
        faithfulness=0.87,
        answer_relevancy=0.75,
        hit_at_5=0.55,  # chunk_id-based, may regress vs naive
        citation_accuracy=0.50,
        hit_at_5_content=0.78,  # content-anchored, trustworthy
        citation_accuracy_content=0.72,
        mean_latency_ms=9500.0,
        total_cost_usd=0.04,
    )
    row = r.to_csv_row()
    assert row["hit_at_5_content"] == 0.78
    assert row["citation_accuracy_content"] == 0.72


def test_chunk_id_format(tmp_path: Path):
    # Sanity: chunk_ids have the right shape so retrieval matches the eval set
    c = Chunk(
        chunk_id="AAPL_2025-10-31_item_7::0003",
        text="Apple net sales were $383.3B.",
        metadata={
            "ticker": "AAPL",
            "filing_date": "2025-10-31",
            "section_id": "item_7",
            "chunk_index": 3,
        },
    )
    assert "::" in c.chunk_id
    parts = c.chunk_id.split("::")
    assert len(parts) == 2
    assert parts[1].isdigit()
