"""
Load and validate hand-authored RPC amendment specs (JSON, no AI).

Used by ``process_amendment.py --amendment-json``. Every change is applied
literally (same code path as offline deterministic parsers).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def load_manual_amendment(path: Path) -> dict[str, Any]:
    """
    Read JSON from *path*, validate, force literal_apply on all changes.

    Expected shape (top-level):
      - amendment_id: str (non-empty)
      - date: str YYYY-MM-DD
      - title: str (optional)
      - changes: list of { article_number, new_text, action? }
      - notes: str (optional, informational only)
    """
    path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Manual amendment spec not found: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    return validate_manual_amendment_payload(raw, source_path=path)


def validate_manual_amendment_payload(
    data: dict[str, Any],
    *,
    source_path: Path | None = None,
) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("Root JSON value must be an object")

    aid = (data.get("amendment_id") or "").strip()
    if not aid:
        raise ValueError("amendment_id is required and must be non-empty")

    date = (data.get("date") or "").strip()
    if not _DATE_RE.match(date):
        raise ValueError(f"date must be YYYY-MM-DD, got {date!r}")

    changes_in = data.get("changes")
    if not isinstance(changes_in, list) or len(changes_in) == 0:
        raise ValueError("changes must be a non-empty array")

    changes_out: list[dict[str, Any]] = []
    for i, ch in enumerate(changes_in):
        if not isinstance(ch, dict):
            raise ValueError(f"changes[{i}] must be an object")
        num = str(ch.get("article_number", "")).strip()
        if not num:
            raise ValueError(f"changes[{i}].article_number is required")
        action = (ch.get("action") or "amend").strip().lower()
        if action not in ("amend", "insert", "repeal"):
            raise ValueError(f"changes[{i}].action must be amend|insert|repeal, got {action!r}")
        if action == "repeal":
            new_text = (ch.get("new_text") or "").strip()
            if new_text:
                raise ValueError(f"changes[{i}]: new_text must be empty when action is repeal")
        else:
            new_text = (ch.get("new_text") or "").strip()
            if not new_text:
                raise ValueError(f"changes[{i}].new_text is required for action={action}")

        entry: dict[str, Any] = {
            "article_number": num,
            "new_text": new_text,
            "action": action,
            "literal_apply": True,
        }
        changes_out.append(entry)

    title = data.get("title")
    title_s = title.strip() if isinstance(title, str) else ""
    notes = data.get("notes")
    notes_s = notes.strip() if isinstance(notes, str) else ""

    out: dict[str, Any] = {
        "amendment_id": aid,
        "date": date,
        "changes": changes_out,
        "literal_apply_all": True,
    }
    if title_s:
        out["title"] = title_s
    if notes_s:
        out["notes"] = notes_s
    if source_path is not None:
        out["_spec_path"] = str(source_path)
    return out


def _self_test() -> None:
    good = validate_manual_amendment_payload(
        {
            "amendment_id": "Republic Act No. 1",
            "date": "1946-01-01",
            "changes": [{"article_number": "1", "new_text": "Art. 1. Example body.", "action": "amend"}],
        }
    )
    assert good["changes"][0]["literal_apply"] is True
    try:
        validate_manual_amendment_payload({"amendment_id": "x", "date": "bad", "changes": []})
    except ValueError:
        pass
    else:
        raise AssertionError("expected invalid date to raise")


if __name__ == "__main__":
    _self_test()
    print("manual_amendment_spec: self-tests OK")
