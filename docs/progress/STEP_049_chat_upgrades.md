# STEP_049 — Chat upgrades: rename, history search, cache badge

- **Date:** 2026-09-20
- **Git commit:** PENDING (this step)
- **Goal:** The three user-asked chat upgrades in one pass. No ledger change.
- **Roadmap phase:** Product, by request (rename/search/badge)

### 1. Why
History without search doesn't scale; auto-titles aren't always right; and the STEP_045 cache was invisible in the UI — users couldn't tell a $0 answer from a fresh one.

### 2. What changed (files — this commit)
- `ui/chat_store.py` — `rename_chat` (blank raises, 80-char word-cut) + `search_chats` (casefold substring over titles + message bodies, newest-first, blank = full list, corrupt files skipped).
- `ui/streamlit_app.py` — `query_api_with_cache` returns (body, X-Cache); `query_api` signature FROZEN (delegates — all old tests pass unmodified); sidebar search box + rename expander; ⚡ badge on fresh cached answers and `· ⚡cached` in history captions (persisted in message meta).
- `tests/test_chat_store.py` (+8: rename ×3, search ×5), `tests/test_ui.py` (+3: HIT/MISS/unknown/body-only; `_Resp` stub gained headers).
- `README.md` — generator-refreshed (247 tests) + `ui/` structure line.
- `docs/progress/STEP_049_*` (this file) + `PROGRESS.md` index update.
- NOT changed: API, ledger (15 rows), eval set.

### 3. How to verify
```bash
make serve; make ui  # search old chats, rename one, repeat a question -> ⚡ badge
uv run pytest tests/test_chat_store.py tests/test_ui.py -q  # 37 passed
```

### 4. Result
Full suite: 247 passed, 0 skipped. Ruff clean except the shared E402 sys.path pattern. One behavioral note: `query_api` now routes through `query_api_with_cache` — identical behavior, verified by the untouched old tests.

### 5. How to recall
- STEP file: `docs/progress/STEP_049_chat_upgrades.md`
- Store: `ui/chat_store.py` (rename/search); badge: `query_api_with_cache` + `cached` in message meta

### 6. Next step
None filed. Remaining wishlist from STEP_048 (semantic near-match cache, shared Redis cache, auth) is untouched — say which, if any.
