# exp_045 analysis — hybrid + multi-query: expansion noise survives the hybrid base

- **Run:** 2026-09-20 (4969s), 139 Q / 4447 chunks, $0.0375.
- **Ledger:** cr=0.8471, fa=0.9286, ar=0.7542, hit@5=0.6259, cite=0.5755, **content=0.7842**, cite_content=0.7554.
- **Baseline exp_021 (hybrid):** content=0.8129, cite_content=0.7986.
- **Paired (non-OOS, n=121):** gained 1 (`q_0065`), lost 5 (`q_0032`, `q_0085`, `q_0107`, `q_0120`, `q_0124`) — net −4, two-sided p~0.22 (noise). Cite pairing: +1/−5, same story.
- **Reading:** multiquery was noise on dense (+4, p~0.42, exp_043) and is noise-minus on hybrid (−4, p~0.22). Three extra Flash paraphrases per Q buy nothing: hybrid's BM25 side already covers the lexical variation expansion was supposed to add, and the extra rankings dilute RRF. Cost per run roughly doubles retrieval-side Flash calls for zero gain.
- **Verdict:** RETIRED on hybrid too. Expansion stays off everywhere; flag remains for future strategies.
