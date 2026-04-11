#!/usr/bin/env python3
"""
Set flashcard_concepts.bar_2026_aligned using the 2026 Bar syllabus files + Gemini.

Reads all .md and .txt under LexCode/docs/2026 Bar/ (UTF-8). Put official syllabi there as plain text.

API: Google AI (Gemini developer API), not Vertex, unless you adapt the URL.

Exact model strings (pick one with --model):
  gemini-3-flash-preview     — Gemini 3 Flash preview (default)
  gemini-2.5-flash           — Gemini 2.5 Flash (stable)
  gemini-2.5-flash-lite      — lighter / cheaper
  gemini-2.0-flash           — older Flash

Vertex AI (your curl style) uses a different base URL, e.g.:
  https://aiplatform.googleapis.com/v1/publishers/google/models/gemini-2.5-flash-lite:generateContent

Env:
  GEMINI_API_KEY or GOOGLE_API_KEY — required (never commit keys)
  DB_CONNECTION_STRING — or Values in api/local.settings.json

Prerequisites:
  sql/flashcard_bar2026_migration.sql applied
  Syllabus text files present under LexCode/docs/2026 Bar/

Examples:
  python scripts/label_flashcard_bar2026_gemini.py --dry-run --limit 40
  python scripts/label_flashcard_bar2026_gemini.py --batch-size 18 --sleep 1.2
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

_ROOT = Path(__file__).resolve().parent.parent
_API = _ROOT / "api"
_SYLLABI = _ROOT / "LexCode" / "docs" / "2026 Bar"

_api_path = str(_API)
if _api_path not in sys.path:
    sys.path.insert(0, _api_path)

import psycopg2  # noqa: E402
from psycopg2.extras import RealDictCursor  # noqa: E402

try:
    import requests
except ImportError:
    print("Install requests: pip install requests", file=sys.stderr)
    sys.exit(1)

def _inject_local_settings_env() -> None:
    """Same pattern as api/classify_subtopics.py: optional keys in local.settings.json."""
    p = _API / "local.settings.json"
    if not p.is_file():
        return
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        for k, v in (data.get("Values") or {}).items():
            if k not in os.environ and v is not None and str(v).strip():
                os.environ[k] = str(v).strip()
    except Exception:
        pass


def _load_db_url() -> str:
    env = os.environ.get("DB_CONNECTION_STRING", "").strip()
    if env:
        return env
    p = _API / "local.settings.json"
    if p.is_file():
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        return (data.get("Values") or {}).get("DB_CONNECTION_STRING", "").strip()
    return ""


def _load_api_key(*, vertex: bool) -> str:
    if vertex:
        k = os.environ.get("GEMINI_VERTEX_API_KEY", "").strip()
        if k:
            return k
    k = (
        os.environ.get("GEMINI_API_KEY", "").strip()
        or os.environ.get("GOOGLE_API_KEY", "").strip()
    )
    if k:
        return k
    p = _API / "local.settings.json"
    if p.is_file():
        data = json.loads(p.read_text(encoding="utf-8"))
        v = data.get("Values") or {}
        if vertex:
            vk = (v.get("GEMINI_VERTEX_API_KEY") or "").strip()
            if vk:
                return vk
        return (
            (v.get("GEMINI_API_KEY") or v.get("GOOGLE_API_KEY") or "").strip()
        )
    return ""


def load_syllabus_text(folder: Path, max_chars: int) -> str:
    if not folder.is_dir():
        raise SystemExit(
            f"Missing syllabus folder: {folder}\n"
            "Create it and add .md / .txt files (see LexCode/docs/2026 Bar/README.md)."
        )
    parts: List[str] = []
    for path in sorted(folder.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in (".md", ".txt"):
            continue
        if path.name.lower() in ("readme.md", "readme.txt"):
            continue
        try:
            parts.append(f"=== FILE: {path.relative_to(folder)} ===\n{path.read_text(encoding='utf-8')}")
        except OSError as e:
            print(f"[warn] skip {path}: {e}", file=sys.stderr)
    blob = "\n\n".join(parts).strip()
    if not blob:
        raise SystemExit(f"No .md or .txt syllabus files under {folder}")
    if len(blob) > max_chars:
        print(
            f"[warn] Syllabus truncated from {len(blob)} to {max_chars} chars "
            "(add --max-syllabus-chars or split files).",
            file=sys.stderr,
        )
        blob = blob[:max_chars]
    return blob


def _strip_json_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z0-9]*\s*", "", t)
        t = re.sub(r"\s*```\s*$", "", t)
    return t.strip()


def call_gemini(
    model: str,
    api_key: str,
    system_text: str,
    user_text: str,
    temperature: float,
    timeout: int,
    use_vertex: bool,
) -> str:
    if use_vertex:
        # Vertex AI publisher endpoint — camelCase fields per API guide
        base = f"https://aiplatform.googleapis.com/v1/publishers/google/models/{model}:generateContent"
        body: Dict[str, Any] = {
            "systemInstruction": {
                "role": "user",
                "parts": [{"text": system_text}],
            },
            "contents": [{"role": "user", "parts": [{"text": user_text}]}],
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json",
            },
        }
    else:
        # Google AI Studio — same shape but snake_case works there too
        base = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        body = {
            "system_instruction": {"parts": [{"text": system_text}]},
            "contents": [{"role": "user", "parts": [{"text": user_text}]}],
            "generationConfig": {
                "temperature": temperature,
                "response_mime_type": "application/json",
            },
        }
    url = f"{base}?{urlencode({'key': api_key})}"
    last_err = None
    for attempt in range(6):
        try:
            r = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                json=body,
                timeout=timeout,
            )
        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
            last_err = str(e)
            wait = 10 + attempt * 5
            print(f"[retry {attempt+1}/6] network/timeout: {e!r} — waiting {wait}s", file=sys.stderr)
            time.sleep(wait)
            continue
        if r.status_code == 429:
            last_err = r.text[:500]
            wait = 8 + attempt * 5
            print(f"[retry {attempt+1}/6] 429 rate limit — waiting {wait}s", file=sys.stderr)
            time.sleep(wait)
            continue
        if r.status_code == 503 or r.status_code == 500:
            last_err = r.text[:500]
            wait = 10 + attempt * 5
            print(f"[retry {attempt+1}/6] HTTP {r.status_code} — waiting {wait}s", file=sys.stderr)
            time.sleep(wait)
            continue
        if r.status_code >= 400:
            raise RuntimeError(f"Gemini HTTP {r.status_code}: {r.text[:800]}")
        break
    else:
        raise RuntimeError(f"Gemini failed after retries: {last_err}")
    data = r.json()
    cands = data.get("candidates") or []
    if not cands:
        raise RuntimeError(f"No candidates in response: {json.dumps(data)[:800]}")
    parts = (cands[0].get("content") or {}).get("parts") or []
    if not parts:
        raise RuntimeError(f"No parts in candidate: {json.dumps(cands[0])[:800]}")
    return parts[0].get("text") or ""


def parse_alignment_json(raw: str, expected_keys: List[str]) -> Dict[str, bool]:
    text = _strip_json_fence(raw)
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("Model output is not a JSON array")
    exp = set(expected_keys)
    out: Dict[str, bool] = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        k = item.get("term_key")
        if not k or str(k) not in exp:
            continue
        aligned = item.get("aligned")
        if isinstance(aligned, str):
            aligned = aligned.strip().lower() in ("1", "true", "yes")
        out[str(k)] = bool(aligned)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Label bar_2026_aligned via Gemini + 2026 Bar syllabi")
    parser.add_argument(
        "--syllabi-dir",
        type=Path,
        default=_SYLLABI,
        help="Folder with .md/.txt syllabus files",
    )
    parser.add_argument("--model", default="gemini-3-flash-preview", help="Gemini model id (Google AI)")
    parser.add_argument(
        "--vertex",
        action="store_true",
        help="Use aiplatform.googleapis.com/publishers/google/models/... (set GEMINI_VERTEX_API_KEY)",
    )
    parser.add_argument("--batch-size", type=int, default=15, help="Concepts per API call")
    parser.add_argument("--limit", type=int, default=0, help="Max concepts to process (0 = all)")
    parser.add_argument("--temperature", type=float, default=0.15)
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--sleep", type=float, default=0.8, help="Seconds between batches")
    parser.add_argument("--max-syllabus-chars", type=int, default=120_000)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--rescan-all",
        action="store_true",
        help="Process all rows (overwrite labels). Default is only bar_2026_aligned IS NULL.",
    )
    args = parser.parse_args()

    _inject_local_settings_env()

    api_key = _load_api_key(vertex=args.vertex)
    if not api_key and not args.dry_run:
        print("Set GEMINI_API_KEY or GOOGLE_API_KEY.", file=sys.stderr)
        sys.exit(1)

    conn_str = _load_db_url()
    if not conn_str:
        print("DB_CONNECTION_STRING missing.", file=sys.stderr)
        sys.exit(1)
    if ":5432/" in conn_str:
        conn_str = conn_str.replace(":5432/", ":5432/")

    syllabus = load_syllabus_text(args.syllabi_dir.resolve(), args.max_syllabus_chars)

    system = (
        "You are a Philippine Bar exam preparation assistant. You must follow the JSON contract exactly.\n"
        "Given the OFFICIAL 2026 Bar examination syllabi (user message includes them) and a list of legal "
        "concepts from Supreme Court digests, decide whether each concept is something a 2026 Bar candidate "
        "should reasonably study given those syllabi.\n"
        "Be inclusive for concepts that clearly fall under any subject or subtopic in the syllabi; exclude "
        "concepts that are hyper-niche, purely procedural oddities, or clearly outside the 2026 scope.\n"
        "Output ONLY a JSON array, no markdown. Each element: {\"term_key\": string, \"aligned\": boolean}.\n"
        "You MUST include every term_key from the batch exactly once."
    )

    def _make_conn() -> "psycopg2.connection":
        c = psycopg2.connect(conn_str, connect_timeout=120)
        c.autocommit = False
        return c

    def _load_rows(c: "psycopg2.connection") -> List[Any]:
        cur2 = c.cursor(cursor_factory=RealDictCursor)
        cur2.execute(
            """
            SELECT term_key, term, definition
            FROM flashcard_concepts
            """
            + ("" if args.rescan_all else "WHERE bar_2026_aligned IS NULL ")
            + "ORDER BY term_key"
        )
        r = cur2.fetchall() or []
        cur2.close()
        return r

    conn = _make_conn()
    try:
        rows = _load_rows(conn)
    except Exception as e:
        conn.close()
        print(f"DB error (run sql/flashcard_bar2026_migration.sql?): {e}", file=sys.stderr)
        sys.exit(1)

    if args.limit and args.limit > 0:
        rows = rows[: args.limit]

    if not rows:
        print("No rows to process.")
        conn.close()
        return

    total_batches = (len(rows) + args.batch_size - 1) // args.batch_size
    print(
        f"Model: {args.model}  |  batches ~{total_batches}  |  rows {len(rows)}"
        f"  |  batch_size {args.batch_size}  |  timeout {args.timeout}s"
    )

    if args.dry_run:
        for i in range(0, len(rows), args.batch_size):
            if i == 0:
                chunk = rows[i : i + args.batch_size]
                lines2 = []
                for r in chunk:
                    term = (r.get("term") or "").replace("\n", " ").strip()
                    defin = (r.get("definition") or "").replace("\n", " ").strip()[:600]
                    lines2.append(f"- term_key: {r['term_key']}\n  term: {term}\n  definition: {defin}")
                user_msg_dry = (
                    "=== 2026 BAR SYLLABI (SOURCE TEXT) ===\n"
                    + syllabus
                    + "\n\n=== CONCEPTS TO CLASSIFY ===\n"
                    + "\n".join(lines2)
                    + "\n\nReturn JSON array only."
                )
                print("\n--- DRY RUN first user message (truncated) ---\n")
                print(user_msg_dry[:2500] + ("\n… [truncated]\n" if len(user_msg_dry) > 2500 else ""))
                break
        print(f"\nDry run: would call Gemini ~{total_batches} times for {len(rows)} concepts.")
        conn.close()
        return

    total_written = 0

    for i in range(0, len(rows), args.batch_size):
        batch_num = i // args.batch_size + 1
        chunk = rows[i : i + args.batch_size]
        expected = [str(r["term_key"]) for r in chunk]
        if batch_num == 1 or batch_num % 20 == 0:
            print(f"[batch {batch_num}/{total_batches}] rows {i+1}–{min(i+args.batch_size, len(rows))} ...")

        lines = []
        for r in chunk:
            term = (r.get("term") or "").replace("\n", " ").strip()
            defin = (r.get("definition") or "").replace("\n", " ").strip()
            if len(defin) > 600:
                defin = defin[:600] + "…"
            lines.append(f"- term_key: {r['term_key']}\n  term: {term}\n  definition: {defin}")
        user_msg = (
            "=== 2026 BAR SYLLABI (SOURCE TEXT) ===\n"
            + syllabus
            + "\n\n=== CONCEPTS TO CLASSIFY ===\n"
            + "\n".join(lines)
            + "\n\nReturn JSON array only."
        )

        raw = call_gemini(
            args.model,
            api_key,
            system,
            user_msg,
            args.temperature,
            args.timeout,
            args.vertex,
        )
        try:
            got = parse_alignment_json(raw, expected)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"[error] batch {batch_num}: parse failed: {e}\nRaw: {raw[:1200]}", file=sys.stderr)
            conn.close()
            sys.exit(1)

        missing = [k for k in expected if k not in got]
        if missing:
            print(f"[warn] batch {batch_num}: missing keys, defaulting False: {missing[:5]}…", file=sys.stderr)

        batch_updates = [(got.get(k, False), k) for k in expected]

        # Commit each batch immediately so partial progress is never lost
        for attempt in range(4):
            try:
                if conn.closed:
                    conn = _make_conn()
                wcur = conn.cursor()
                wcur.executemany(
                    """
                    UPDATE flashcard_concepts
                    SET bar_2026_aligned = %s,
                        bar_2026_labeled_at = now()
                    WHERE term_key = %s
                    """,
                    batch_updates,
                )
                conn.commit()
                wcur.close()
                total_written += len(batch_updates)
                break
            except psycopg2.OperationalError as db_err:
                print(f"[db-retry {attempt+1}/4] {db_err} — reconnecting…", file=sys.stderr)
                try:
                    conn.close()
                except Exception:
                    pass
                time.sleep(5 + attempt * 5)
                conn = _make_conn()
        else:
            print(f"[fatal] DB write failed after retries on batch {batch_num}", file=sys.stderr)
            conn.close()
            sys.exit(1)

        time.sleep(args.sleep)

    conn.close()
    print(f"Updated {total_written} rows.")

    try:
        from cache import cache_delete  # type: ignore
        from config import FLASHCARD_CONCEPTS_CACHE_KEY  # type: ignore

        if cache_delete(FLASHCARD_CONCEPTS_CACHE_KEY):
            print(f"Invalidated Redis key {FLASHCARD_CONCEPTS_CACHE_KEY!r}.")
    except Exception as inv_ex:
        print(f"[note] Redis cache invalidation skipped: {inv_ex}")


if __name__ == "__main__":
    main()
