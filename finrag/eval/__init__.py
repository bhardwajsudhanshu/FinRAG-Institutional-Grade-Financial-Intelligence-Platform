"""Evaluation package: RAGAS runner + experiment harness.

The eval pipeline is:
1. Load the frozen Q&A set (data/eval/qa_pairs.jsonl, v1 = 139 Q's
   across 20 tickers; see ADR-003)
2. Build the chunk + index for each eval filing (parse -> chunk -> embed)
3. For each Q: retrieve top-K chunks, generate an answer
4. Score the (question, retrieved_contexts, response, reference) tuple with
   RAGAS metrics: context_recall, faithfulness, answer_relevancy
5. Aggregate per-experiment and append a row to results/experiments.csv
6. Optionally stream per-Q records to a JSONL file as the run progresses,
   so a long run survives a crash.

The RAGAS integration is intentionally thin: we build an
`EvaluationDataset` of `SingleTurnSample`s and call `ragas.evaluate()`.
"""

from finrag.eval.ragas_runner import (
    ExperimentResult,
    build_index_for_qa_pairs,
    run_experiment,
)
from finrag.eval.metrics import span_appears_in_chunk

__all__ = [
    "ExperimentResult",
    "build_index_for_qa_pairs",
    "run_experiment",
    "span_appears_in_chunk",
]
