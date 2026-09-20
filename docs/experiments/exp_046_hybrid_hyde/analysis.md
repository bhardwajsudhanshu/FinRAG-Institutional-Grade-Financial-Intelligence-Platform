# exp_046 analysis — hybrid + HyDE: a $0.01 wash

- **Run:** 2026-09-20 (4808s), 139 Q / 4447 chunks, $0.0368. One RAGAS-judge `TimeoutError` mid-run (Job[361], retried inside the runner — final row complete, 139/139 per-Q).
- **Ledger:** cr=0.8636, fa=0.8763, ar=0.7614, hit@5=0.6619, cite=0.5971, **content=0.8058**, cite_content=0.7842.
- **Baseline exp_021 (hybrid):** content=0.8129, cite_content=0.7986.
- **Paired (non-OOS, n=121):** gained 5 (`q_0005`, `q_0019`, `q_0065`, `q_0116`, `q_0118`), lost 6 (`q_0026`, `q_0032`, `q_0079`, `q_0093`, `q_0119`, `q_0120`) — net −1, p~1.0. Cite pairing identical (+5/−6).
- **Reading:** HyDE helped dense (+8, suggestive) because dense had headroom; hybrid has none to give — the hypothetical doc retrieves what the BM25 side already finds. +139 Flash writes (~$0.01/run) for a statistical tie.
- **Curiosity:** `q_0065` is the single Q gained by BOTH combos; `q_0032`/`q_0120` lost in both — expansion and HyDE perturb the same rankings, they don't complement.
- **Verdict:** RETIRED as a combo. HyDE stays kept-not-default for dense-only (exp_044). The question-side program is closed: multiquery noise twice, HyDE wash on hybrid.
