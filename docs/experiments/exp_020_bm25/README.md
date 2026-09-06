# exp_020_bm25

## Hypothesis

BM25 (exact lexical match) beats dense cosine on lookup Q's carrying
rare exact strings — dollar figures ("$383.3 billion"), tickers, "Item
1A" — and loses on section/synthesis Q's phrased as paraphrase. This is
the ablation ADR-004 demands before any hybrid: each side's contribution
measured alone on the frozen set, same naive chunks as exp_001 (4447),
same generator, fixed OOS logic.

## Setup

- **Chunker**: `naive` (identical chunks to exp_001 — retrieval effect isolated)
- **Retrieval**: `bm25` (`BM25Index` over regex word tokens, no embeddings at retrieval time)
- **Generator / judge**: unchanged (Flash / Flash + text-embedding-005)
- top_k=5, eval v1 139 Q.

## What changes vs. exp_001

| Component | exp_001 | exp_020 |
|---|---|---|
| Chunks | naive 512/50 | identical |
| Retrieval | dense cosine (Vertex embed per Q) | BM25 (CPU, free) |
| Generator | Flash | identical |

## Evaluation

Smoke (~2 min, no embedding calls except generator context — cheap):

```bash
CHUNKER_STRATEGY=naive RETRIEVAL_STRATEGY=bm25 uv run python -m finrag.cli.eval --exp exp_020_bm25 --limit 6 --smoke
```

Full (~30 min — no chunk-embed phase at all — STEP_013):

```bash
CHUNKER_STRATEGY=naive RETRIEVAL_STRATEGY=bm25 uv run python -m finrag.cli.eval --exp exp_020_bm25
```

Expect: lookup hit_content up vs dense; section/synthesis down; overall the
`retrieval` leaderboard category (context_recall) gets a data point that is
*not* expected to win — the win comes in exp_021 hybrid. Results in
`analysis.md` after the full run.
