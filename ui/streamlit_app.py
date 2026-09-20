"""FinRAG chat UI (STEP_048; dashboard since STEP_021).

ChatGPT-style: left sidebar holds every conversation (persisted in
`ui/chats/*.json`, gitignored), main panel is the active thread.
Calls the FastAPI service over HTTP — run it first:
    make serve        # terminal 1 (hybrid retrieval, in-memory)
    make ui           # terminal 2 (this app)
    # FINRAG_API_URL=http://host:8000 make ui   # non-default API address

Only `main()` touches streamlit (runs under `streamlit run`); the helpers
above plus `ui/chat_store.py` stay importable and unit-testable.
"""

from __future__ import annotations

import os

import httpx


def api_url() -> str:
    """Base URL of the FinRAG API (env override for docker/remote)."""
    return os.environ.get("FINRAG_API_URL", "http://localhost:8000").rstrip("/")


def query_api(question: str, top_k: int = 5, rerank: bool = False,
              timeout_s: float = 180.0) -> dict:
    """POST /ask. Raises RuntimeError with a human message on any failure."""
    try:
        resp = httpx.post(f"{api_url()}/ask",
                          json={"question": question, "top_k": top_k, "rerank": rerank},
                          timeout=timeout_s if not rerank else max(timeout_s, 300.0))
    except httpx.ConnectError as e:
        raise RuntimeError(
            f"API unreachable at {api_url()} — start it with `make serve`."
        ) from e
    except httpx.TimeoutException as e:
        raise RuntimeError(f"API timed out after {timeout_s:.0f}s — try again.") from e
    if resp.status_code == 422:
        raise RuntimeError("Please enter a question (1-2000 chars) and top_k 1-20.")
    if resp.status_code != 200:
        raise RuntimeError(f"API error {resp.status_code}: {resp.text[:200]}")
    return resp.json()


def fetch_health(timeout_s: float = 5.0) -> dict | None:
    """GET /health. Returns None (no raise) when the API is down."""
    try:
        resp = httpx.get(f"{api_url()}/health", timeout=timeout_s)
        return resp.json() if resp.status_code == 200 else None
    except Exception:
        return None


def fetch_leaderboard_winners(timeout_s: float = 10.0) -> list[tuple[str, str, object]]:
    """Flatten GET /leaderboard categories to [(category, winner, value)]."""
    try:
        resp = httpx.get(f"{api_url()}/leaderboard", timeout=timeout_s)
        if resp.status_code != 200:
            return []
        cats = resp.json().get("categories", {})
        return [(name, info.get("winner"), info.get("winner_value"))
                for name, info in sorted(cats.items())]
    except Exception:
        return []


def main() -> None:
    import streamlit as st

    from ui.chat_store import (
        DEFAULT_DIR,
        append_turn,
        delete_chat,
        list_chats,
        load_chat,
        new_chat,
        save_chat,
    )

    st.set_page_config(page_title="FinRAG", layout="wide")

    # --- session state: which chat is open --------------------------------
    if "chat_id" not in st.session_state:
        st.session_state.chat_id = None
    if "chat" not in st.session_state:
        st.session_state.chat = None

    def open_chat(chat_id: str | None) -> None:
        if chat_id is None:
            st.session_state.chat = None
        else:
            st.session_state.chat = load_chat(DEFAULT_DIR, chat_id)
        st.session_state.chat_id = chat_id

    # --- sidebar: conversations -------------------------------------------
    with st.sidebar:
        st.header("Chats")
        if st.button("+ New chat", use_container_width=True):
            open_chat(None)
            st.rerun()
        for summary in list_chats(DEFAULT_DIR):
            label = summary["title"]
            if summary["n_messages"]:
                label += f" ({summary['n_messages']})"
            active = summary["id"] == st.session_state.chat_id
            if st.button(("▶ " if active else "") + label,
                         key=f"chat-{summary['id']}",
                         use_container_width=True,
                         disabled=active):
                open_chat(summary["id"])
                st.rerun()
        st.divider()
        if st.session_state.chat_id and st.button("Delete this chat"):
            delete_chat(DEFAULT_DIR, st.session_state.chat_id)
            open_chat(None)
            st.rerun()
        st.divider()
        st.header("Settings")
        top_k = st.slider("Top-K chunks", min_value=1, max_value=20, value=5)
        rerank = st.checkbox("Best answer (Flash re-rank, ~30s, bills calls)",
                             value=False)
        st.divider()
        health = fetch_health()
        if health is None:
            st.warning(f"API down at {api_url()} — run `make serve` first.")
        else:
            st.success(f"Index ready: {health.get('n_chunks', '?')} chunks")
            st.caption(f"{health.get('retrieval_strategy', '?')} over "
                       f"{health.get('vectordb_backend', '?')} · "
                       f"{health.get('generator_model', '?')}")

    # --- main: active thread ------------------------------------------------
    chat = st.session_state.chat
    st.title(chat["title"] if chat else "FinRAG — Financial Intelligence")
    if chat is None:
        st.caption("Ask about SEC 10-K filings. History lives in the sidebar; "
                   "each chat remembers its own thread.")
    else:
        for msg in chat["messages"]:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                if msg["role"] == "assistant":
                    _render_answer_meta(msg)

    question = st.chat_input("Ask about 10-K filings…")
    if question:
        if chat is None:
            chat = new_chat(top_k=top_k, rerank=rerank)
            st.session_state.chat = chat
        chat["settings"] = {"top_k": top_k, "rerank": rerank}
        append_turn(chat, "user", question)
        with st.chat_message("user"):
            st.write(question)
        with st.chat_message("assistant"):
            with st.spinner("Retrieving + generating…"):
                try:
                    res = query_api(question, top_k=top_k, rerank=rerank)
                except RuntimeError as e:
                    st.error(str(e))
                    chat["messages"].pop()  # don't persist failed turns
                    if chat["messages"]:
                        save_chat(DEFAULT_DIR, chat)
                        st.session_state.chat_id = chat["id"]
                    return
            st.write(res.get("answer", ""))
            msg_meta = _render_answer_meta({
                "citations": res.get("citations", []),
                "meta": {
                    "model": res.get("model", "?"),
                    "input_tokens": res.get("input_tokens", 0),
                    "output_tokens": res.get("output_tokens", 0),
                    "cost_usd": res.get("cost_usd", 0.0),
                    "latency_ms": res.get("latency_ms", 0),
                    "reranked": bool(res.get("reranked")),
                },
            })
        append_turn(chat, "assistant", res.get("answer", ""),
                    citations=res.get("citations", []), meta=msg_meta)
        save_chat(DEFAULT_DIR, chat)
        st.session_state.chat_id = chat["id"]
        st.rerun()


def _render_answer_meta(msg: dict) -> dict:
    """Render citations + cost caption for an assistant message.

    Takes {citations, meta} (works for stored messages and fresh API
    responses alike) and returns the meta dict for persistence.
    Import-safe: streamlit import lives with the caller.
    """
    import streamlit as st

    meta = msg.get("meta", {}) or {}
    cites = msg.get("citations", []) or []
    if cites:
        with st.expander(f"Sources ({len(cites)})", expanded=False):
            st.table([{"chunk": c.get("chunk_id", ""),
                       "ticker": c.get("ticker", ""),
                       "section": c.get("section_id", ""),
                       "score": round(float(c.get("score", 0.0)), 3)}
                      for c in cites])
    else:
        st.caption("No citations — the model refused (out-of-scope question?).")
    st.caption(f"Model {meta.get('model', '?')} · "
               f"{meta.get('input_tokens', 0)} in / {meta.get('output_tokens', 0)} out · "
               f"${float(meta.get('cost_usd', 0.0)):.4f} · {meta.get('latency_ms', 0)}ms"
               + (" · re-ranked" if meta.get("reranked") else ""))
    return meta


if __name__ == "__main__":
    main()
