"""RAGAS evaluation runner for FinRAG experiments.

Loads a frozen Q&A set (tests/eval/qa_pairs.jsonl), builds the in-memory
chunk+embedding index for the eval filings, runs the full RAG pipeline
(retrieve -> generate) for each Q, and scores the result with three RAGAS
metrics:

- context_recall: did the retrieved chunks contain the ground-truth answer?
- faithfulness:   is the generated answer supported by the retrieved chunks?
- answer_relevancy: is the generated answer relevant to the question?

Plus three cheap custom metrics we compute ourselves (no LLM judge):

- hit@5:         fraction of Q's where the source chunk is in the top-5 retrieved
- citation_acc:  fraction of Q's where the generated answer's citations
                 include the source chunk
- mean_latency:  average end-to-end latency in ms

Usage
-----
    from finrag.eval import run_experiment
    result = run_experiment(
        exp_name="exp_001_naive_baseline",
        qa_path="data/eval/qa_pairs.jsonl",
    )
    print(result.to_dict())

The full set of eval filings is built from data/raw/filings.parquet
(whatever filings are referenced by the Q&A set). This means the runner
is self-contained: it does not require an external vector DB.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger

from finrag.chunking import chunk_sections_by_strategy
from finrag.config import get_settings
from finrag.data.parse_sections import parse_filing
from finrag.generation import get_generator
from finrag.retrieval import build_index, retrieve, results_to_citations


# --- Result schema ---------------------------------------------------------

@dataclass
class ExperimentResult:
    """The output of one experiment run. Persists to experiments.csv."""

    exp_name: str
    timestamp: str
    n_questions: int
    n_filings: int
    n_chunks: int
    # RAGAS metrics (None if the run failed before RAGAS)
    context_recall: float | None
    faithfulness: float | None
    answer_relevancy: float | None
    # Custom metrics
    hit_at_5: float
    citation_accuracy: float
    mean_latency_ms: float
    # Cost
    total_cost_usd: float
    # Raw per-Q records (for debugging; written separately to a JSONL)
    per_question: list[dict[str, Any]] = field(default_factory=list)

    def to_csv_row(self) -> dict[str, Any]:
        """One row for results/experiments.csv. Drops the bulky per_question."""
        d = asdict(self)
        d.pop("per_question", None)
        return d


# --- Index builder ---------------------------------------------------------

def _qa_pairs_to_dataframe(qa_path: Path) -> pd.DataFrame:
    """Load the Q&A JSONL file into a DataFrame."""
    rows: list[dict] = []
    with qa_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    df = pd.DataFrame(rows)
    logger.info(f"Loaded {len(df)} Q&A pairs from {qa_path}")
    return df


def build_index_for_qa_pairs(
    qa_path: Path,
    processed_dir: Path | None = None,
) -> tuple[Any, pd.DataFrame, dict[str, str]]:
    """Build the in-memory index for the filings referenced by the Q&A set.

    Returns (index, qa_df, chunk_id_to_text). The chunk_id_to_text map is
    used to compute hit@5 cheaply.
    """
    settings = get_settings()
    processed_dir = processed_dir or settings.data_processed_dir
    qa_df = _qa_pairs_to_dataframe(qa_path)

    # Find which filings we need: the most recent (ticker, filing_date) pair
    # for each Q. For each unique filing, parse + chunk + embed.
    manifest_path = settings.data_raw_dir / "filings.parquet"
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"No filings manifest at {manifest_path}. Run `make ingest` first."
        )
    manifest = pd.read_parquet(manifest_path)
    manifest["key"] = manifest["ticker"] + "|" + manifest["filing_date"].astype(str)
    key_to_path = dict(zip(manifest["key"], manifest["local_path"]))

    # Pick the unique (ticker, filing_date) pairs referenced by the Q set.
    # Prefer the Q's own source_filing_date so the chunks line up.
    eval_keys = set()
    for _, q in qa_df.iterrows():
        key = f"{q['source_ticker']}|{q['source_filing_date']}"
        eval_keys.add(key)
    logger.info(f"Eval set references {len(eval_keys)} unique filings")

    # Build chunks for each filing
    all_chunks = []
    for key in eval_keys:
        if key not in key_to_path:
            logger.warning(f"Q references missing filing {key}, skipping")
            continue
        local_path = Path(key_to_path[key])
        ticker, filing_date = key.split("|", 1)
        # Pull fiscal_year from the manifest
        m = manifest[manifest["key"] == key].iloc[0]
        fy = int(m.get("fiscal_year", 0))
        accession = m.get("accession_number", "")
        html = local_path.read_text(encoding="utf-8")
        sections = parse_filing(html)
        if not sections:
            logger.warning(f"No sections parsed for {key}, skipping")
            continue
        chunks = chunk_sections_by_strategy(
            settings.chunker_strategy,
            sections=sections,
            ticker=ticker,
            filing_date=filing_date,
            fiscal_year=fy,
            accession_number=accession,
        )
        all_chunks.extend(chunks)
        logger.info(
            f"  [{key}] parsed {len(sections)} sections, {len(chunks)} chunks "
            f"(chunker={settings.chunker_strategy})"
        )
    logger.info(f"Total chunks to embed: {len(all_chunks)}")

    if not all_chunks:
        raise RuntimeError("No chunks produced for eval set; check filing paths.")

    # Embed + index
    index = build_index(all_chunks)
    chunk_id_to_text = {c.chunk_id: c.text for c in all_chunks}
    return index, qa_df, chunk_id_to_text


# --- Experiment runner -----------------------------------------------------

def _hit_at_k(retrieved_chunk_ids: list[str], source_chunk_id: str, k: int) -> bool:
    return source_chunk_id in retrieved_chunk_ids[:k]


def run_experiment(
    exp_name: str,
    qa_path: Path,
    top_k: int | None = None,
    ragas_batch_size: int = 10,
    per_q_out: Path | None = None,
) -> ExperimentResult:
    """Run one experiment end-to-end and return an ExperimentResult.

    The function:
    1. Builds the in-memory index for the eval filings
    2. For each Q: retrieve top-K, generate an answer, capture metrics
    3. Computes hit@5, citation_accuracy, mean_latency (custom)

    If `per_q_out` is provided, each per-Q record is appended to that
    JSONL file as it's computed, so a long run survives a crash and you
    can monitor progress.

    4. Calls ragas.evaluate() for context_recall/faithfulness/answer_relevancy
    5. Returns an ExperimentResult ready to append to experiments.csv

    `ragas_batch_size` controls how many Q's we send to RAGAS at once
    (smaller = more parallel LLM calls, lower memory; default 10).
    """
    settings = get_settings()
    if top_k is None:
        top_k = settings.retrieval_top_k
    t0 = time.perf_counter()

    index, qa_df, chunk_id_to_text = build_index_for_qa_pairs(qa_path)
    embed_seconds = time.perf_counter() - t0
    logger.info(f"Index built in {embed_seconds:.1f}s ({len(index)} chunks)")

    generator = get_generator()

    # --- Per-Q retrieve + generate --------------------------------------
    per_q: list[dict[str, Any]] = []
    ragas_rows: list[dict[str, Any]] = []
    hit_count = 0
    citation_hit = 0
    latencies: list[int] = []
    total_cost = 0.0

    # Optional incremental per-Q output so a long run survives a crash
    per_q_fh = None
    if per_q_out is not None:
        per_q_out.parent.mkdir(parents=True, exist_ok=True)
        per_q_fh = per_q_out.open("w", encoding="utf-8")

    for i, (_, q) in enumerate(qa_df.iterrows()):
        qid = q["id"]
        question = q["question"]
        source_chunk_id = q["source_chunk_id"]
        ground_truth = q["ground_truth_answer"]
        is_oos = q.get("qa_type") == "out_of_scope"

        t_q = time.perf_counter()
        try:
            retrieved = retrieve(index, question, top_k=top_k)
        except Exception as e:
            logger.warning(f"[{qid}] retrieval failed: {e}")
            retrieved = []

        # Build context list for the generator
        if retrieved:
            cites = results_to_citations(retrieved)
            contexts = [(c.text, cites[j]) for j, (c, _s) in enumerate(retrieved)]
            retrieved_chunk_ids = [c.chunk_id for c, _ in retrieved]
        else:
            contexts = []
            retrieved_chunk_ids = []

        # hit@K (only meaningful for non-OOS Q's)
        if not is_oos and _hit_at_k(retrieved_chunk_ids, source_chunk_id, top_k):
            hit_count += 1
        elif is_oos:
            # OOS Q's: we count "hit" only if the source chunk is *not* retrieved
            if source_chunk_id not in retrieved_chunk_ids:
                hit_count += 1

        try:
            gen_result = generator.generate(question, contexts)
            answer_text = gen_result.answer
            generated_chunk_ids = {c.chunk_id for c in gen_result.citations}
            total_cost += gen_result.cost_usd
            if is_oos:
                # For OOS, "citation accuracy" means: did the model NOT cite
                # any real chunk? We want the model to say "I cannot find this".
                # If no chunks cited AND the answer starts with "I cannot", +1
                if not generated_chunk_ids and "I cannot" in answer_text:
                    citation_hit += 1
            else:
                if source_chunk_id in generated_chunk_ids:
                    citation_hit += 1
        except Exception as e:
            logger.warning(f"[{qid}] generation failed: {e}")
            answer_text = ""
            generated_chunk_ids = set()

        latency_ms = int((time.perf_counter() - t_q) * 1000)
        latencies.append(latency_ms)

        per_q.append({
            "qid": qid,
            "question": question,
            "ground_truth": ground_truth,
            "source_chunk_id": source_chunk_id,
            "qa_type": q.get("qa_type"),
            "retrieved_chunk_ids": retrieved_chunk_ids,
            "generated_chunk_ids": list(generated_chunk_ids),
            "answer": answer_text,
            "latency_ms": latency_ms,
        })
        # Incremental save: write the per-Q record to disk so we can
        # monitor progress and survive crashes on long runs.
        if per_q_fh is not None:
            per_q_fh.write(json.dumps(per_q[-1], ensure_ascii=False) + "\n")
            per_q_fh.flush()
        # Build the RAGAS row.
        # For OOS Q's, we use the ground truth (which is something like
        # "I cannot find this in the provided filings.") and an empty
        # retrieved_contexts list, so RAGAS metrics behave sanely.
        # (RAGAS was designed for non-OOS Q's; we exclude OOS from RAGAS
        # to avoid noise.)
        if not is_oos and retrieved:
            ragas_rows.append({
                "user_input": question,
                "retrieved_contexts": [c.text for c, _ in retrieved],
                "response": answer_text,
                "reference": ground_truth,
            })
        if (i + 1) % 25 == 0:
            logger.info(f"  ...processed {i + 1}/{len(qa_df)} Q's")

    n = len(qa_df)
    hit_at_5 = hit_count / n if n else 0.0
    citation_acc = citation_hit / n if n else 0.0
    mean_lat = sum(latencies) / len(latencies) if latencies else 0.0

    # --- RAGAS scoring -------------------------------------------------
    cr, fa, ar = (None, None, None)
    if ragas_rows:
        cr, fa, ar = _score_with_ragas(ragas_rows, batch_size=ragas_batch_size)

    elapsed = time.perf_counter() - t0
    logger.info(
        f"Experiment {exp_name!r} done in {elapsed:.1f}s. "
        f"hit@5={hit_at_5:.3f}, cite_acc={citation_acc:.3f}, "
        f"cr={cr}, fa={fa}, ar={ar}, cost=${total_cost:.4f}"
    )

    if per_q_fh is not None:
        per_q_fh.close()

    return ExperimentResult(
        exp_name=exp_name,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
        n_questions=n,
        n_filings=len({q["source_ticker"] + q["source_filing_date"] for _, q in qa_df.iterrows()}),
        n_chunks=len(index),
        context_recall=cr,
        faithfulness=fa,
        answer_relevancy=ar,
        hit_at_5=hit_at_5,
        citation_accuracy=citation_acc,
        mean_latency_ms=mean_lat,
        total_cost_usd=total_cost,
        per_question=per_q,
    )


def _score_with_ragas(
    rows: list[dict[str, Any]],
    batch_size: int = 10,
) -> tuple[float | None, float | None, float | None]:
    """Run RAGAS on a list of {user_input, retrieved_contexts, response, reference}.

    Returns (context_recall, faithfulness, answer_relevancy). Each is None
    if RAGAS could not compute it (e.g., import error or empty list).

    Note: `answer_relevancy` requires an embeddings model; we pass our
    Vertex text-embedding-005 via `GoogleEmbeddings` so RAGAS doesn't fall
    back to OpenAI (which we don't have a key for).
    """
    try:
        from datasets import Dataset
        from ragas.dataset_schema import EvaluationDataset, SingleTurnSample
        from ragas.evaluation import evaluate
        from ragas.llms import LangchainLLMWrapper
        from ragas.metrics import answer_relevancy, context_recall, faithfulness
    except Exception as e:
        logger.error(f"RAGAS import failed: {e}")
        return None, None, None

    settings = get_settings()

    # RAGAS needs an LLM judge. Use Gemini 2.5 Flash via Vertex — same
    # auth/SDK setup as our generator. We wrap the langchain ChatVertexAI
    # in a LangchainLLMWrapper so ragas can call it.
    try:
        from langchain_google_vertexai import ChatVertexAI
        lc_llm = ChatVertexAI(
            model="gemini-2.5-flash",
            project=settings.gcp_project_id,
            location=settings.gcp_region,
            temperature=0.0,
        )
        judge_llm = LangchainLLMWrapper(lc_llm)
    except Exception as e:
        logger.error(f"Could not build RAGAS judge LLM: {e}")
        return None, None, None

    # answer_relevancy uses an embedder. We pass our existing Vertex
    # embedder via the LangchainEmbeddingsWrapper — `ragas.embeddings.GoogleEmbeddings`
    # in 0.4.3 doesn't expose the right interface for answer_relevancy yet,
    # so we go through langchain-google-vertexai which has the right
    # `embed_query` method.
    judge_embeddings = None
    try:
        from langchain_google_vertexai import VertexAIEmbeddings
        from ragas.embeddings import LangchainEmbeddingsWrapper
        # vertexai.init may already have been called; this is a no-op then
        import vertexai  # type: ignore
        vertexai.init(project=settings.gcp_project_id, location=settings.gcp_region)
        lc_embedder = VertexAIEmbeddings(
            model_name="text-embedding-005",
            project=settings.gcp_project_id,
            location=settings.gcp_region,
        )
        judge_embeddings = LangchainEmbeddingsWrapper(lc_embedder)
    except Exception as e:
        logger.warning(
            f"Could not build Vertex-backed RAGAS embeddings ({e}); "
            "answer_relevancy will be skipped."
        )
        judge_embeddings = None

    samples = [
        SingleTurnSample(
            user_input=r["user_input"],
            retrieved_contexts=r["retrieved_contexts"],
            response=r["response"],
            reference=r["reference"],
        )
        for r in rows
    ]
    eval_ds = EvaluationDataset(samples=samples)

    metrics = [context_recall, faithfulness]
    if judge_embeddings is not None:
        metrics.append(answer_relevancy)

    try:
        kwargs: dict[str, Any] = {
            "dataset": eval_ds,
            "metrics": metrics,
            "llm": judge_llm,
            "show_progress": False,
            "batch_size": batch_size,
            "raise_exceptions": False,
        }
        if judge_embeddings is not None:
            kwargs["embeddings"] = judge_embeddings
        result = evaluate(**kwargs)
    except Exception as e:
        logger.error(f"ragas.evaluate() failed: {e}")
        return None, None, None

    # ragas 0.4.x returns an EvaluationResult with a `.scores` list of
    # per-row dicts. Compute column means manually (no pandas dependency).
    def _mean(col: str) -> float | None:
        try:
            scores = result.scores if hasattr(result, "scores") else None
            if not scores:
                return None
            vals = [row.get(col) for row in scores if row.get(col) is not None]
            # Drop NaN
            import math
            vals = [v for v in vals if not (isinstance(v, float) and math.isnan(v))]
            if not vals:
                return None
            return float(sum(vals) / len(vals))
        except Exception as e:
            logger.warning(f"Could not extract {col} from ragas result: {e}")
            return None

    cr = _mean("context_recall")
    fa = _mean("faithfulness")
    ar = _mean("answer_relevancy") if judge_embeddings is not None else None
    return cr, fa, ar
