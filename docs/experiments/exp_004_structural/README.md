# exp_004_structural

## Hypothesis

Uniform chunk budgets are wrong for 10-Ks because sections have different
discourse shapes (ADR-001). Risk Factors (Item 1A) are enumerated lists —
small chunks align with list items so one risk rarely shares a chunk with
three others. MD&A (Item 7) is flowing narrative — wide windows keep the
fact and its surrounding causal context together. Financials (Item 8) are
tables — splitting mid-table orphans numbers from row labels.

vs exp_002 (uniform 2000/200 recursive) this should raise `context_recall`
(facts keep their context) with FEWER chunks than semantic's 6858 (no
embedding-driven fragmentation — splitting is still paragraph-aware
recursion, only budgets vary). vs exp_003 it concedes topic-coherence but
bets document structure is the cheaper signal. First full run scored under
the fixed OOS logic (STEP_009), so its `hit_at_5_content` is directly
comparable to future chunkers (not to frozen exp_001/002 rows).

## Setup

- **Chunker**: `structural` (`finrag/chunking.py::chunk_sections_structural`)
- **Budgets** (chars, LangChain-style): 1a/1b/1c → 1200/200; 1/2/3/7a → 2000/200 (= recursive default); 7/8 → 3000/200. Unknown sections → 2000/200 fallback (never crashes).
- **Splitter**: `recursive_chunk_text` per section (no embedding at chunk time — index build should run at exp_002 speed, not exp_003's 64 min).
- **Metadata**: `chunker="structural"` + `section_budget` per chunk.
- Everything else identical (vertex embed/gen, top_k=5, eval v1 139 Q).

## What changes vs. exp_002 / exp_003

| Component | exp_002 | exp_003 | exp_004 |
|---|---|---|---|
| Chunker | recursive 2000/200 uniform | semantic P95 | structural per-section budgets |
| Chunk-time cost | 0 embed | ~2× embed | 0 embed |
| Expected n_chunks | 5412 | 6858 | between 4447–5412 |

## Evaluation

Smoke (cheap, ~4 min, AAPL only):

```bash
CHUNKER_STRATEGY=structural uv run python -m finrag.cli.eval --exp exp_004_structural --limit 6 --smoke
```

Full (~45 min — no sentence-embedding phase — STEP_011):

```bash
CHUNKER_STRATEGY=structural uv run python -m finrag.cli.eval --exp exp_004_structural
```

Decision metric: `context_recall` (target: beat 0.8058 naive) + `hit_at_5_content` under fixed OOS logic + n_chunks. Results in `analysis.md` after the full run.
