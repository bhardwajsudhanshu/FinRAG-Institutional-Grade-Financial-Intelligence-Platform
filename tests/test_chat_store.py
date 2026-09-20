"""Chat-store tests (STEP_048). Fully offline, tmp dirs only."""

from __future__ import annotations

import json
import sys
from pathlib import Path

# tests/ -> project root
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest

from ui.chat_store import (
    append_turn,
    delete_chat,
    list_chats,
    load_chat,
    new_chat,
    rename_chat,
    save_chat,
    search_chats,
    title_for,
)


class TestTitles:
    def test_short_question_kept(self) -> None:
        assert title_for("Apple revenue?") == "Apple revenue?"

    def test_long_title_cuts_at_word(self) -> None:
        t = title_for("What was Apple's total net sales in fiscal year 2023 exactly?")
        assert t.endswith("…")
        assert len(t) <= 44
        assert "…" not in t[:-1]

    def test_whitespace_collapsed(self) -> None:
        assert title_for("  Apple\n  revenue?  ") == "Apple revenue?"

    def test_empty_falls_back(self) -> None:
        assert title_for("   ") == "New chat"


class TestRoundTrip:
    def test_new_save_load(self, tmp_path: Path) -> None:
        chat = new_chat(top_k=3, rerank=True)
        assert chat["title"] == "New chat"
        assert chat["settings"] == {"top_k": 3, "rerank": True}
        save_chat(tmp_path, chat)
        loaded = load_chat(tmp_path, chat["id"])
        assert loaded is not None
        assert loaded["messages"] == []
        assert loaded["settings"]["top_k"] == 3

    def test_missing_returns_none(self, tmp_path: Path) -> None:
        assert load_chat(tmp_path, "nope") is None

    def test_corrupt_raises_loudly(self, tmp_path: Path) -> None:
        (tmp_path / "bad.json").write_text("{not json", encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            load_chat(tmp_path, "bad")

    def test_bad_id_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            load_chat(tmp_path, "../evil")


class TestListAndDelete:
    def test_newest_first(self, tmp_path: Path) -> None:
        # Fixed timestamps (same-second saves would tie — sort must be explicit).
        for cid, ts in (("aaa", "2026-09-20T10:00:00+00:00"),
                        ("bbb", "2026-09-20T12:00:00+00:00")):
            chat = new_chat()
            chat["id"] = cid
            chat["created_at"] = ts
            (tmp_path / f"{cid}.json").write_text(
                json.dumps({**chat, "updated_at": ts}), encoding="utf-8")
        assert [s["id"] for s in list_chats(tmp_path)] == ["bbb", "aaa"]

    def test_corrupt_skipped(self, tmp_path: Path) -> None:
        (tmp_path / "broken.json").write_text("xx", encoding="utf-8")
        good = new_chat()
        save_chat(tmp_path, good)
        assert [s["id"] for s in list_chats(tmp_path)] == [good["id"]]

    def test_empty_dir(self, tmp_path: Path) -> None:
        assert list_chats(tmp_path / "missing") == []

    def test_delete(self, tmp_path: Path) -> None:
        chat = new_chat()
        save_chat(tmp_path, chat)
        assert delete_chat(tmp_path, chat["id"]) is True
        assert load_chat(tmp_path, chat["id"]) is None
        assert delete_chat(tmp_path, chat["id"]) is False


class TestAppendTurn:
    def test_first_question_titles_chat(self) -> None:
        chat = new_chat()
        append_turn(chat, "user", "What was Apple's revenue in FY2023?")
        assert chat["title"] == "What was Apple's revenue in FY2023?"

    def test_assistant_keeps_title(self) -> None:
        chat = new_chat()
        append_turn(chat, "user", "Revenue?")
        append_turn(chat, "assistant", "A", citations=[], meta={"model": "m"})
        assert chat["title"] == "Revenue?"
        assert chat["messages"][1]["meta"] == {"model": "m"}

    def test_bad_role_rejected(self) -> None:
        with pytest.raises(ValueError):
            append_turn(new_chat(), "system", "x")


class TestRename:
    def test_rename(self, tmp_path: Path) -> None:
        chat = new_chat()
        append_turn(chat, "user", "Revenue?")
        rename_chat(chat, "  Q3 deep dive  ")
        assert chat["title"] == "Q3 deep dive"
        save_chat(tmp_path, chat)
        assert load_chat(tmp_path, chat["id"])["title"] == "Q3 deep dive"

    def test_blank_rejected(self) -> None:
        with pytest.raises(ValueError):
            rename_chat(new_chat(), "   ")

    def test_long_title_cut_at_word(self) -> None:
        chat = rename_chat(new_chat(), "x" * 30 + " " + "y" * 60)
        assert chat["title"] == "x" * 30  # cut back to the word boundary


class TestSearch:
    def _seed(self, tmp_path: Path) -> None:
        a = new_chat()
        append_turn(a, "user", "What was Apple revenue?")
        append_turn(a, "assistant", "383B", citations=[], meta={})
        save_chat(tmp_path, a)
        b = new_chat()
        append_turn(b, "user", "Microsoft Azure growth?")
        save_chat(tmp_path, b)

    def test_finds_in_messages(self, tmp_path: Path) -> None:
        self._seed(tmp_path)
        hits = search_chats(tmp_path, "azure")
        assert len(hits) == 1
        assert hits[0]["title"] == "Microsoft Azure growth?"

    def test_case_insensitive_title(self, tmp_path: Path) -> None:
        self._seed(tmp_path)
        assert len(search_chats(tmp_path, "APPLE")) == 1

    def test_no_match(self, tmp_path: Path) -> None:
        self._seed(tmp_path)
        assert search_chats(tmp_path, "tesla") == []

    def test_blank_query_lists_all(self, tmp_path: Path) -> None:
        self._seed(tmp_path)
        assert len(search_chats(tmp_path, "   ")) == 2

    def test_missing_dir(self, tmp_path: Path) -> None:
        assert search_chats(tmp_path / "nope", "x") == []
