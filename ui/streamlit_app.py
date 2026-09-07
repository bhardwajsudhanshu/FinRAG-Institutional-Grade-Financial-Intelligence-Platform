"""FinRAG demo dashboard (STEP_021 product surface).

Calls the FastAPI service over HTTP — run it first:
    make serve        # terminal 1 (hybrid retrieval, in-memory)
    make ui           # terminal 2 (this dashboard)
    # FINRAG_API_URL=http://host:8000 make ui   # non-default API address

UI code lives in `main()` (executed only under `streamlit run`) so the
pure helpers below stay importable and unit-testable without a browser.
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

    st.set_page_config(page_title="FinRAG", layout="wide")
    st.title("FinRAG — Financial Intelligence over SEC filings")

    with st.sidebar:
        st.header("Backend")
        health = fetch_health()
        if health is None:
            st.warning(f"API down at {api_url()} — run `make serve` first.")
        else:
            st.success(f"Index ready: {health.get('n_chunks', '?')} chunks")
            st.caption(f"{health.get('retrieval_strategy', '?')} over "
                       f"{health.get('vectordb_backend', '?')} · "
                       f"{health.get('generator_model', '?')}")
        st.header("Leaderboard")
        winners = fetch_leaderboard_winners()
        if winners:
            st.table([{"track": c, "leader": w or "—"} for c, w, _ in winners])
        else:
            st.caption("Leaderboard unavailable.")

    question = st.text_input("Ask about 10-K filings",
                             value="What was Apple's revenue in FY2023?")
    top_k = st.slider("Top-K chunks", min_value=1, max_value=20, value=5)
    rerank = st.checkbox("Best answer (Flash re-rank, ~30s, bills scoring calls)",
                         value=False)
    if st.button("Ask", type="primary"):
        if not question.strip():
            st.error("Please enter a question.")
            return
        with st.spinner("Retrieving + generating..."):
            try:
                res = query_api(question, top_k=top_k, rerank=rerank)
            except RuntimeError as e:
                st.error(str(e))
                return
        st.subheader("Answer")
        st.write(res.get("answer", ""))
        st.subheader("Sources")
        cites = res.get("citations", [])
        if cites:
            st.table([{"chunk": c.get("chunk_id", ""), "ticker": c.get("ticker", ""),
                       "section": c.get("section_id", ""),
                       "score": round(float(c.get("score", 0.0)), 3)} for c in cites])
        else:
            st.caption("No citations — the model refused (out-of-scope question?).")
        st.caption(f"Model {res.get('model', '?')} · "
                   f"{res.get('input_tokens', 0)} in / {res.get('output_tokens', 0)} out tokens · "
                   f"${res.get('cost_usd', 0.0):.4f} · {res.get('latency_ms', 0)}ms"
                   + (" · re-ranked" if res.get("reranked") else ""))


if __name__ == "__main__":
    main()
