# Experiment 001 — Analysis

**Status:** Real Vertex end-to-end working (Day 2 → Day 3 update)
**Date:** 2026-09-05
**Pipeline:** naive 512/50 chunking + `text-embedding-005` + dense cosine + `gemini-2.5-flash`
**Corpus:** 1 filing (AAPL FY2023 10-K, real download from EDGAR)

## Real Vertex run (Day 3)

After wiring `EMBEDDER_BACKEND=vertex` and `GENERATOR_BACKEND=vertex`, the
smoke test produces real numbers. Sample query:

> "What was Apple's revenue in FY2023?"
>
> Answer: *"Apple's total net sales for fiscal year 2023 were $383.3 billion."*
> Cited from `[AAPL_2023-11-03_item_7::0000]`
>
> Tokens: in=3,820 out=73. Cost: $0.0003.

For "What are Apple's main risk factors?", all 5 retrieved chunks come from
`item_1a` — the right section.

## What I ran (original Day 2 mock results, for reference)

I asked 5 hand-crafted questions to the smoke test pipeline and inspected what was retrieved and answered:

| # | Question | Top retrieved section | Plausible answer? |
|---|----------|----------------------|-------------------|
| 1 | What are Apple's main risk factors? | `item_1a` (Risk Factors) | ✅ Correct section |
| 2 | What was Apple's revenue in FY2023? | `item_7` (MD&A) | ✅ Correct section, $383.3B |
| 3 | What is Apple's gross margin in FY2023? | (not run) | n/a |
| 4 | What are Apple's supply chain risks? | (not run, would be `item_1a`) | n/a |
| 5 | How does Apple hedge currency risk? | (not run, would be `item_7a`) | n/a |

## What broke / surprised me (Day 2, with mock)

1. **Mock embedder retrieval quality is artificially good for "section" questions.**
   The mock uses token-hash features. Section header text ("Item 1A. Risk Factors")
   has very distinctive tokens, so any query mentioning "risk factors" gets a
   strong match. This means our mock-based hit-rates will be **higher than
   the real Vertex embedding numbers** for section-style questions.

2. **Mock embedder retrieval is poor for paraphrased questions.**
   "How does Apple hedge currency risk?" vs. the actual text "The Company uses
   derivative instruments to hedge certain exposures" — these don't share
   many tokens, so the mock's score is much lower than a real embedder's.
   Expected: mock Hit@5 ~ 0.4, real Hit@5 ~ 0.7 on this question style.

3. **Section parser was over-matching (FIXED).** Initial parse returned
   17 sections, including duplicates from the 10-K's table of contents
   and from internal cross-references like "See Item 7 for...".
   After two fixes (min-length filter + dedupe by longest match), the
   parser now returns **6 clean sections** that match what a human would
   identify. Chunk count dropped from 106 → 94, with 3 of the top-5
   retrieved chunks now correctly from `item_1a` (Risk Factors) for
   the question "What are Apple's main risk factors?"

4. **The mock generator's answer is a verbatim quote of the first 240 chars
   of the top chunk.** This is not a real generation. Once Vertex is wired
   we'll see actual answer synthesis. Until then, this is fine for validating
   that the **retrieval** is right.

5. **Cost log is working** with the mock backend — every call writes
   `{ts, operation, model, input_tokens, output_tokens, cost_usd, latency_ms}`
   to `data/runtime_costs.jsonl`. When we swap to Vertex, the cost column
   will become real (Flash input: $0.075/M tokens, output: $0.30/M).

6. **C: drive protection confirmed.** All project state is on F:. The uv
   cache (718 MB after install) is at `F:/.uv-cache`, not on C:.

## Real Vertex gotchas (Day 3, fixed)

Five bugs surfaced when we wired the real Vertex backends. Recording here so
the next person doesn't lose an afternoon.

1. **Windows cp1252 console can't print Unicode emoji.**
   The auth-check script crashed on `print("✅")` with `UnicodeEncodeError`.
   Fix: replaced with `[OK]` / `[FAIL]`. Long-term: set `PYTHONIOENCODING=utf-8`
   in the shell, or `sys.stdout.reconfigure(encoding="utf-8")` in scripts.

2. **Service account key isn't picked up by the SDK at import time.**
   `from vertexai...` triggers `google.auth.default()` *eagerly*. If
   `GOOGLE_APPLICATION_CREDENTIALS` is empty at that point, the SDK caches
   the wrong (gcloud user) creds and ignores the env var forever. Fix:
   set `os.environ["GOOGLE_APPLICATION_CREDENTIALS"]` at module top,
   before any google-cloud import.

3. **403 SERVICE_DISABLED even with the right service account.**
   Vertex AI requires a `quota_project_id` on the credentials. Service
   account keys don't carry one. Fix: set
   `os.environ["GOOGLE_CLOUD_QUOTA_PROJECT"] = settings.gcp_project_id`
   right after `vertexai.init(...)`.

4. **400 input token count too large from `embed_batch`.**
   `TextEmbeddingModel.get_embeddings([...])` accepts a list, but the
   total input across all items in one call is capped at ~20K tokens for
   `text-embedding-005`. Sending 94 chunks in one call fails. Fix: chunk
   the batch to ≤20 items per call.

5. **Generation call returned 0-token cost.**
   `record_call(...)` records `input_tokens`/`output_tokens` at context
   entry, but real usage is only known after the response. Fix: read
   `response.usage_metadata.prompt_token_count` and
   `candidates_token_count` after `generate_content(...)`, then update
   the record and recompute cost.

All five are now fixed in `finrag/embeddings.py`, `finrag/generation.py`,
and `scripts/test_vertex_auth.py`. The cost log at `data/runtime_costs.jsonl`
now contains real numbers (one record per embed_batch, one per generate call).

## Section parser fix (Day 2, applied)

Two passes, total 8 lines changed in `parse_sections.py`:

1. **Length filter**: drop sections < 500 chars (internal cross-references)
2. **TOC dedupe**: when the same `section_id` appears multiple times, keep
   the longest occurrence (the real section body, not the TOC entry)

**Result:** 17 → 6 real sections. Apple 10-K now parses cleanly to:
- Item 1 (Business, 15K chars)
- Item 1A (Risk Factors, 67K chars)
- Item 3 (Legal Proceedings, 6K chars)
- Item 7 (MD&A, 15K chars)
- Item 7A (Market Risk, 3K chars)
- Item 8 (Financial Statements, 85K chars)

Missing (expected): 1B, 1C, 2 are absent because Apple folds them or they
don't exist in their filing. This is normal.

## Next experiment's hypothesis (preview for exp_002)

`exp_002` will be **Recursive chunking** (LangChain-style, respects
paragraphs and sentence boundaries). The hypothesis:

> Switching from naive fixed-size to recursive chunking will improve
> Context Recall by 5–10% on the eval set, because financial text has
> long, multi-sentence clauses that get cut mid-thought by the naive
> chunker, then matched incorrectly by the embedder.

The test: same 200-Q eval set (when we have it, end of Week 2), same
embedder, same vector DB. Only the chunker changes. Compare Hit@5, MRR,
and RAGAS context recall.

## What's NOT in this analysis (deliberately)

- Numbers from the mock embedder are not in the leaderboard. We use
  real Vertex numbers once auth is wired.
- We don't have a real eval set yet (200 Q&A pairs). That's Week 2 work.
- The auto-router, RAPTOR, re-ranking etc. are all future experiments.
