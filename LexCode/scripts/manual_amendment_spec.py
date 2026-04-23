"""
**Literal ingestion** for RPC amendments: hand-authored JSON, no AI.

Use this path when a law implies **complex structural changes** (e.g. reclassification under
RA 8353): the statute text in the JSON is the **immutable blob**—the system must not paraphrase,
summarize, or reformat it. ``process_amendment --amendment-json`` applies each ``new_text`` as
literal codal content (same storage rules as deterministic offline extracts: ``normalize_storage_markdown``
only for safe fixes in ``codal_text``).

This bypasses generative parsing so punctuation and wording match the Republic Act exactly.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Columns on ``rpc_codal`` that amendments may override (e.g. new chapter under RA 8353).
_RPC_CODAL_KEYS = frozenset(
    {
        "book",
        "book_label",
        "title_num",
        "title_label",
        "chapter_label",
        "chapter_num",
        "section_label",
        "section_num",
    }
)


def _normalize_rpc_codal_payload(raw: Any, *, index: int) -> dict[str, Any] | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError(f"changes[{index}].rpc_codal must be an object when present")
    out: dict[str, Any] = {}
    for k, v in raw.items():
        if k not in _RPC_CODAL_KEYS:
            raise ValueError(f"changes[{index}].rpc_codal: unknown key {k!r}")
        if v is None:
            continue
        if k in ("book", "title_num", "chapter_num", "section_num"):
            if isinstance(v, bool):
                raise ValueError(f"changes[{index}].rpc_codal.{k}: invalid boolean")
            if isinstance(v, str) and v.strip().lstrip("-").isdigit():
                out[k] = int(v.strip())
            elif isinstance(v, (int, float)) and not isinstance(v, bool):
                out[k] = int(v)
            else:
                raise ValueError(
                    f"changes[{index}].rpc_codal.{k} must be a number, got {type(v).__name__}"
                )
        else:
            if not isinstance(v, str):
                raise ValueError(
                    f"changes[{index}].rpc_codal.{k} must be a string, got {type(v).__name__}"
                )
            s = v.strip()
            if not s:
                continue
            out[k] = s
    return out or None


def load_manual_amendment(path: Path) -> dict[str, Any]:
    """
    Read JSON from *path*, validate, force literal_apply on all changes.

    Expected shape (top-level):
      - amendment_id: str (non-empty)
      - date: str YYYY-MM-DD
      - title: str (optional)
      - amendment_description: str (optional) — default narrative for all changes on literal
        apply when a change has no ``amendment_description`` (stored in ``article_versions`` /
        ``rpc_codal.amendments``).
      - changes: list of { article_number, new_text, action?, rpc_codal?, amendment_description? }
        Per-change ``amendment_description`` overrides the top-level default for that article.
        Optional ``rpc_codal`` sets ``rpc_codal`` present-view columns when syncing (new chapter,
        title move, etc.). Keys: book, book_label, title_num, title_label, chapter_num,
        chapter_label, section_num, section_label (numeric fields as JSON numbers).
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
        ch_desc = (ch.get("amendment_description") or "").strip()
        if ch_desc:
            entry["amendment_description"] = ch_desc
        rc = _normalize_rpc_codal_payload(ch.get("rpc_codal"), index=i)
        if rc:
            entry["rpc_codal"] = rc
        changes_out.append(entry)

    title = data.get("title")
    title_s = title.strip() if isinstance(title, str) else ""
    notes = data.get("notes")
    notes_s = notes.strip() if isinstance(notes, str) else ""
    top_desc = data.get("amendment_description")
    top_desc_s = top_desc.strip() if isinstance(top_desc, str) else ""

    out: dict[str, Any] = {
        "amendment_id": aid,
        "date": date,
        "changes": changes_out,
        "literal_apply_all": True,
    }
    if title_s:
        out["title"] = title_s
    if top_desc_s:
        out["amendment_description"] = top_desc_s
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
    with_struct = validate_manual_amendment_payload(
        {
            "amendment_id": "Republic Act No. 8353",
            "date": "1997-09-30",
            "changes": [
                {
                    "article_number": "266-A",
                    "action": "insert",
                    "new_text": "Article 266-A. Rape.",
                    "rpc_codal": {
                        "book": 2,
                        "book_label": "BOOK TWO",
                        "title_num": 8,
                        "title_label": "CRIMES AGAINST PERSONS",
                        "chapter_num": 3,
                        "chapter_label": "RAPE",
                    },
                }
            ],
        }
    )
    assert with_struct["changes"][0]["rpc_codal"]["chapter_num"] == 3
    with_desc = validate_manual_amendment_payload(
        {
            "amendment_id": "Republic Act No. 6968",
            "date": "1990-10-24",
            "amendment_description": "Default card for all changes.",
            "changes": [
                {
                    "article_number": "100",
                    "new_text": "Art. 100. Body.",
                    "action": "amend",
                    "amendment_description": "Per-article override.",
                }
            ],
        }
    )
    assert with_desc["amendment_description"] == "Default card for all changes."
    assert with_desc["changes"][0]["amendment_description"] == "Per-article override."
    try:
        validate_manual_amendment_payload({"amendment_id": "x", "date": "bad", "changes": []})
    except ValueError:
        pass
    else:
        raise AssertionError("expected invalid date to raise")


if __name__ == "__main__":
    _self_test()
    print("manual_amendment_spec: self-tests OK")
