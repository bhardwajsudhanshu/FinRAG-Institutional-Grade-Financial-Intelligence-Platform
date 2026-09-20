# STEP_048 — ChatGPT-style chat UI (sidebar history, persisted threads)

- **Date:** 2026-09-20
- **Git commit:** PENDING (this step)
- **Goal:** Ask questions in a real chat UI with memory across sessions. No ledger change.
- **Roadmap phase:** Product (user-requested; roadmap was empty, this reopens it by request)

### 1. Why
The old dashboard was one-shot Q&A — no history, no threads. Daily use needs conversations you can return to.

### 2. What changed (files — this commit)
- `ui/chat_store.py` (new) — conversation persistence: one JSON per chat in `ui/chats/` (gitignored, private); first-question auto-titles; newest-first listing; corrupt files skipped in list but loud on direct load; FIFO-free (chats are small, histories are the asset).
- `ui/streamlit_app.py` — `main()` rewritten ChatGPT-style: sidebar (＋New chat, clickable history with message counts, delete-current, top_k/rerank settings, backend health) + main thread (`st.chat_message` history, `st.chat_input`, expandable Sources, cost/latency caption). Failed turns are not persisted. API helpers untouched (`query_api` signature frozen — tests pin it).
- `tests/test_chat_store.py` (new, 15 tests) — titles, round-trip, corrupt-loud, id validation, ordering, delete, failed-role rejection.
- `.gitignore` — `ui/chats/` (history never commits).
- `README.md` — generator-refreshed (236 tests) + product row + `ui/` structure line.
- `docs/progress/STEP_048_*` (this file) + `PROGRESS.md` index update.
- NOT changed: API, ledger (15 rows), eval set. Leaderboard table dropped from the sidebar (still served at GET /leaderboard) — sidebar space belongs to chats now.

### 3. How to verify
```bash
make serve   # terminal 1
make ui      # terminal 2 -> ask, reload page, history persists in ui/chats/
uv run pytest tests/test_chat_store.py tests/test_ui.py -q  # 26 passed
```

### 4. Result
Full suite: 236 passed, 0 skipped. Ruff: source files clean after --fix (import style, datetime.UTC, ASCII button label — a fullwidth ＋ broke nothing but RUF001 flagged it); test file carries only the shared E402 sys.path pattern. Module import + store round-trip verified headless. Browser pass is the user's half: `make serve` + `make ui`, ask two questions in one chat, reload — thread must persist via `ui/chats/`.

### 5. How to recall
- STEP file: `docs/progress/STEP_048_chat_ui.md`
- Store: `ui/chat_store.py`; UI: `ui/streamlit_app.py::main`
- Deliberately NOT built: rename-chat, search-history, cross-device sync, auth (local single-user tool).

### 6. Next step
None filed — backlog by request from here (rename/search, semantic near-match cache, shared Redis cache across fleet workers).
