# STEP template — copy for every new implementation

```text
Copy this file to STEP_007_<short_name>.md and fill all sections.
Never edit an old STEP file. Append-only.
```

## STEP_XXX — <short title>

- **Date:**
- **Git commit:** `<hash> <message>` (or `PENDING` if uncommitted)
- **Goal (1 line):**
- **Roadmap phase:** (e.g. Week 3-4 Chunking / exp_003)

### 1. Why (context)
<!-- What problem forced this step? Link ADR if any. -->

### 2. What changed (files)
<!-- List every file created/modified. One line per file with 1-line reason. -->
- `path/to/file.py` —
- `docs/experiments/exp_XXX/` —
- `results/...` —

### 3. How it works (bit-by-bit)
<!-- 3-6 bullets a future-you needs to re-understand the code. Include `file:line` refs. -->

### 4. How to verify
```bash
# exact commands to prove this step works
make test
make lint
```

### 5. Result / numbers
<!-- Metrics, counts, costs. Link experiments.csv row / leaderboard snapshot. -->

### 6. How to recall
- STEP file: `docs/progress/STEP_XXX_*.md`
- Commit: `git show <hash> --stat`
- Experiment: `docs/experiments/exp_XXX/`
- Ledger: `results/experiments.csv`, `results/leaderboard.json`

### 7. Next step
<!-- What does the next STEP pick up? -->
