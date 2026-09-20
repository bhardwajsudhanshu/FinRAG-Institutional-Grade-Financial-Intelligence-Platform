"""Persisted conversations for the FinRAG chat UI (STEP_048).

Each chat is one JSON file in `ui/chats/<chat_id>.json` (gitignored —
private user history never commits):

    {"id": ..., "title": ..., "created_at": ..., "updated_at": ...,
     "settings": {"top_k": 5, "rerank": false},
     "messages": [{"role": "user"|"assistant", "content": ...,
                   "citations": [...], "meta": {...}}]}

All functions are pure stdlib + unit-tested (tests/test_chat_store.py).
The Streamlit layer (streamlit_app.main) only calls these — no file I/O
of its own, so a future backend swap (SQLite, Redis) touches this file.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_DIR = Path(__file__).resolve().parent / "chats"
TITLE_LEN = 42


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _chat_path(chats_dir: Path, chat_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", chat_id):
        raise ValueError(f"bad chat id: {chat_id!r}")
    return chats_dir / f"{chat_id}.json"


def title_for(question: str) -> str:
    """First-question title: collapsed whitespace, cut at a word boundary."""
    text = " ".join(question.split())
    if len(text) <= TITLE_LEN:
        return text or "New chat"
    cut = text[:TITLE_LEN].rsplit(" ", 1)[0]
    return (cut or text[:TITLE_LEN]) + "…"


def new_chat(top_k: int = 5, rerank: bool = False) -> dict:
    now = _now()
    return {"id": uuid.uuid4().hex[:12], "title": "New chat",
            "created_at": now, "updated_at": now,
            "settings": {"top_k": top_k, "rerank": rerank},
            "messages": []}


def save_chat(chats_dir: Path, chat: dict) -> Path:
    """Persist one chat (updates updated_at). Returns the file path."""
    chats_dir.mkdir(parents=True, exist_ok=True)
    chat = dict(chat)
    chat["updated_at"] = _now()
    path = _chat_path(chats_dir, chat["id"])
    path.write_text(json.dumps(chat, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def load_chat(chats_dir: Path, chat_id: str) -> dict | None:
    """Load one chat; None when missing. Raises on corrupt JSON (loud —
    silent history loss is worse than an error)."""
    path = _chat_path(chats_dir, chat_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_chats(chats_dir: Path) -> list[dict]:
    """Newest-first summaries: [{id, title, updated_at, n_messages}].
    Corrupt files are SKIPPED (listed separately would need UI surface;
    the file stays on disk for forensics)."""
    if not chats_dir.exists():
        return []
    summaries = []
    for path in chats_dir.glob("*.json"):
        try:
            chat = json.loads(path.read_text(encoding="utf-8"))
            summaries.append({"id": chat["id"], "title": chat.get("title", "Untitled"),
                              "updated_at": chat.get("updated_at", ""),
                              "n_messages": len(chat.get("messages", []))})
        except (json.JSONDecodeError, KeyError, UnicodeDecodeError):
            continue
    summaries.sort(key=lambda s: s["updated_at"], reverse=True)
    return summaries


def delete_chat(chats_dir: Path, chat_id: str) -> bool:
    """Delete one chat file. Returns True when something was deleted."""
    path = _chat_path(chats_dir, chat_id)
    if not path.exists():
        return False
    path.unlink()
    return True


def append_turn(chat: dict, role: str, content: str,
                citations: list | None = None, meta: dict | None = None) -> dict:
    """Append one message; auto-titles untitled chats on the first question."""
    if role not in ("user", "assistant"):
        raise ValueError(f"bad role: {role!r}")
    msg: dict = {"role": role, "content": content}
    if citations is not None:
        msg["citations"] = citations
    if meta is not None:
        msg["meta"] = meta
    chat["messages"].append(msg)
    if role == "user" and chat.get("title") in (None, "", "New chat"):
        chat["title"] = title_for(content)
    return chat


def rename_chat(chat: dict, new_title: str) -> dict:
    """Rename in place. Blank titles raise (the caller decides UI wording) —
    silently keeping a stale title would confuse the sidebar."""
    title = " ".join(new_title.split())
    if not title:
        raise ValueError("chat title must not be blank")
    if len(title) > 80:
        title = title[:80].rsplit(" ", 1)[0] or title[:80]
    chat["title"] = title
    return chat


def search_chats(chats_dir: Path, query: str) -> list[dict]:
    """Case-insensitive substring search over titles + message contents.
    Returns newest-first summaries (same shape as list_chats). Blank query
    lists everything — the sidebar search box degrades to the full list."""
    if not query.strip():
        return list_chats(chats_dir)
    if not chats_dir.exists():
        return []
    needle = query.casefold()
    hits = []
    for path in chats_dir.glob("*.json"):
        try:
            chat = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, KeyError, UnicodeDecodeError):
            continue
        texts = [str(chat.get("title", ""))]
        for msg in chat.get("messages", []):
            texts.append(str(msg.get("content", "")))
        if any(needle in t.casefold() for t in texts):
            try:
                hits.append({"id": chat["id"],
                             "title": chat.get("title", "Untitled"),
                             "updated_at": chat.get("updated_at", ""),
                             "n_messages": len(chat.get("messages", []))})
            except KeyError:
                continue
    hits.sort(key=lambda s: s["updated_at"], reverse=True)
    return hits
