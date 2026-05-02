#!/usr/bin/env python3
"""
scan_elib_new_cases.py
======================
Scan-only phase of the eLib pipeline. Probes the SC E-Library for new
case URLs that are NOT yet in ``sc_decided_cases`` and writes a JSON
summary to disk. Does **not** fetch full HTML, does not write to the DB,
does not run any digest.

The scan checks each candidate eLib ID for:
  1. Whether the URL already exists in the DB (skip).
  2. Whether the page returns a valid HTTP 200 with case content.
  3. Whether the case is a G.R. docket (not A.M., A.C., etc.).

Output JSON (written to --output path):
  {
    "scanned_at":        "<ISO timestamp>",
    "max_elib_id_in_db": 73500,
    "probed_from":       73501,
    "probed_to":         73900,
    "total_probed":      400,
    "total_new_found":   5,
    "stopped_reason":    "consecutive_misses" | "max_probe_reached",
    "cases": [
      {
        "elib_id":    73502,
        "sc_url":     "https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/73502",
        "case_label": "G.R. No. 277280 | 2025-09-30"
      },
      ...
    ]
  }

Usage:
  python scripts/scan_elib_new_cases.py
  python scripts/scan_elib_new_cases.py --max-probe 200 --output /tmp/scan.json
  python scripts/scan_elib_new_cases.py --start-after 73500
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from load_local_settings_env import load_api_local_settings_into_environ

import psycopg2

ELIB_SHOWDOCS = "https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/"

# Regex to detect G.R. docket in the first 50 KB of the page HTML/text
_GR_PATTERN  = re.compile(r"G\s*\.\s*R\s*\.\s*No\.", re.IGNORECASE)
# Detect valid SC decision pages
_DECISION_PATTERN = re.compile(
    r"D\s*E\s*C\s*I\s*S\s*I\s*O\s*N|R\s*E\s*S\s*O\s*L\s*U\s*T\s*I\s*O\s*N",
    re.IGNORECASE,
)
# Extract case label from the decision header line:  ## [ G.R. No. XXX, Month DD, YYYY ]
_CASE_HEADER = re.compile(
    r"##\s*\[\s*(.+?)\s*,\s*([A-Z][a-z]+\s+\d{1,2},?\s*\d{4})\s*\]",
    re.DOTALL,
)

log = logging.getLogger(__name__)


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://elibrary.judiciary.gov.ph/",
    })
    return s


def _get_last_elib_case(conn) -> dict:
    """Return the highest-ID eLib case already in the DB.

    Returns a dict with elib_id, sc_url, case_label, date (or zeros/empty if none).
    """
    cur = conn.cursor()
    cur.execute(
        r"""
        SELECT
            sc_url,
            CAST(SUBSTRING(sc_url FROM '/showdocs/1/([0-9]+)') AS INTEGER) AS elib_id,
            COALESCE(NULLIF(TRIM(case_number),''), NULLIF(TRIM(short_title),''), '') AS case_label,
            date
        FROM sc_decided_cases
        WHERE sc_url ILIKE %s
          AND sc_url ~ %s
        ORDER BY
            CAST(SUBSTRING(sc_url FROM '/showdocs/1/([0-9]+)') AS INTEGER) DESC
        LIMIT 1
        """,
        (
            "%elibrary.judiciary.gov.ph%thebookshelf/showdocs/1/%",
            r"/showdocs/1/[0-9]+",
        ),
    )
    row = cur.fetchone()
    cur.close()
    if row and row[1]:
        return {
            "elib_id":    int(row[1]),
            "sc_url":     row[0],
            "case_label": (row[2] or "").strip(),
            "date":       str(row[3]) if row[3] else None,
        }
    return {"elib_id": 0, "sc_url": "", "case_label": "", "date": None}


def _url_exists(conn, sc_url: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM sc_decided_cases WHERE sc_url = %s LIMIT 1", (sc_url,))
    found = cur.fetchone() is not None
    cur.close()
    return found


def _probe_page(session: requests.Session, elib_id: int) -> tuple[str, str]:
    """
    Lightweight probe — fetches up to 64 KB of the page.
    Returns (status, snippet) where status is:
      "already_in_db"  — caller should set this before calling this function
      "ok_gr"          — valid page, G.R. docket
      "ok_not_gr"      — valid page, non-G.R. docket (A.M., A.C., etc.)
      "miss"           — 404, error page, no decision content
      "http_error"     — network / non-200 response
    """
    url = f"{ELIB_SHOWDOCS}{elib_id}"
    try:
        r = session.get(url, timeout=40, stream=True)
    except requests.RequestException as exc:
        log.debug("HTTP error for id=%s: %s", elib_id, exc)
        return "http_error", ""

    if r.status_code != 200:
        return "http_error", ""

    # Read first 128 KB — eLib dates often appear well below the GR header
    chunk = b""
    for data in r.iter_content(131072):
        chunk += data
        if len(chunk) >= 131072:
            break
    r.close()

    text = chunk.decode("utf-8", errors="replace")

    # E-Library error page detection
    if "elibrary.judiciary.gov.ph" in text and (
        "The document you requested" in text
        or "Page not found" in text
        or "showdocs/1/" not in url  # safeguard
    ):
        # Check for actual error phrases
        if re.search(r"(The document you requested|not found|does not exist)", text, re.IGNORECASE):
            return "miss", ""

    if not _DECISION_PATTERN.search(text):
        return "miss", ""

    if _GR_PATTERN.search(text[:120000]):
        return "ok_gr", text[:10000]   # pass 10 KB to extraction for better date coverage
    return "ok_not_gr", text[:3000]


def _extract_case_meta(html_snippet: str, elib_id: int) -> dict:
    """Extract GR number(s) and date from an eLib HTML snippet.

    eLib header format (primary target):
        [ G.R. No. 276186, October 29, 2025 ]
        [ G.R. Nos. 276186, 276187, October 29, 2025 ]   ← consolidated

    Returns:
        gr_number    — e.g. "G.R. No. 276186" or "G.R. Nos. 276186, 276187"
        date_decided — e.g. "October 29, 2025"
        case_label   — combined, e.g. "G.R. No. 276186 | October 29, 2025"
    """
    gr_number    = ""
    date_decided = ""

    _MONTHS = (
        r"(?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December)"
    )

    # ── Primary: extract from the eLib header bracket ─────────────────────────
    # Uses [^\]]+ (any char except ], lazy) to handle all GR formats:
    #   [ G.R. No. 276186, October 29, 2025 ]
    #   [ G.R. Nos. 228374-84, 236268, 249296, 254892 & 254906-15, October 28, 2025 ]
    bracket = re.search(
        r"\[\s*"
        r"(G\.?\s*R\.?\s*Nos?\.?\s*[^\]]+?)"   # GR part: any char except ], lazy
        r",\s*"
        rf"({_MONTHS}\s+\d{{1,2}},?\s*\d{{4}})"  # date part
        r"\s*\]",
        html_snippet,
        re.IGNORECASE | re.DOTALL,
    )

    if bracket:
        # Decode HTML entities then normalise whitespace
        raw_gr = bracket.group(1).strip().rstrip(",")
        raw_gr = re.sub(r"&amp;",  "&", raw_gr, flags=re.IGNORECASE)
        raw_gr = re.sub(r"&nbsp;", " ", raw_gr, flags=re.IGNORECASE)
        raw_gr = re.sub(r"&[a-z]+;", "", raw_gr, flags=re.IGNORECASE)
        raw_gr = re.sub(r"\s+", " ", raw_gr).strip()
        raw_gr = re.sub(r"-\s+(\d)", r"-\1", raw_gr)   # fix "254906- 15" → "254906-15"
        date_decided = re.sub(r"\s+", " ", bracket.group(2).strip())

        # Separate numeric portion from the G.R. No(s). prefix
        nums_part = re.sub(
            r"^G\.?\s*R\.?\s*Nos?\.?\s*", "", raw_gr, flags=re.IGNORECASE
        ).strip()
        is_plural = bool(re.search(r",|\band\b|&", nums_part, re.IGNORECASE))
        prefix    = "G.R. Nos." if is_plural else "G.R. No."
        gr_number = f"{prefix} {nums_part}"[:80]

    else:
        # ── Fallback: search the full snippet independently ───────────────────
        m = re.search(
            r"G\.?\s*R\.?\s*Nos?\.?\s*"
            r"((?:\d[\d\-]*)"
            r"(?:(?:\s*,\s*|\s+and\s+|\s*&\s*)\d[\d\-]*)*)",
            html_snippet,
            re.IGNORECASE,
        )
        if m:
            raw_nums  = re.sub(r"\s+", " ", m.group(1).strip().rstrip(","))
            is_plural = bool(re.search(r",|\band\b|&", raw_nums, re.IGNORECASE))
            prefix    = "G.R. Nos." if is_plural else "G.R. No."
            gr_number = f"{prefix} {raw_nums}"[:80]

        # Date — search full snippet
        dm = re.search(
            rf"{_MONTHS}\s+\d{{1,2}},?\s*\d{{4}}",
            html_snippet,
            re.IGNORECASE,
        )
        if dm:
            date_decided = re.sub(r"\s+", " ", dm.group(0).strip())
        else:
            # ISO date fallback: 2025-09-30 → September 30, 2025
            dm2 = re.search(
                r"\b(20\d{2})[-/](0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01])\b",
                html_snippet,
            )
            if dm2:
                import datetime as _dt
                try:
                    parsed = _dt.date(
                        int(dm2.group(1)), int(dm2.group(2)), int(dm2.group(3))
                    )
                    date_decided = parsed.strftime("%B %d, %Y")
                except ValueError:
                    date_decided = dm2.group(0)

    case_label = " | ".join(filter(None, [gr_number, date_decided])) or f"eLib #{elib_id}"
    return {
        "gr_number":    gr_number,
        "date_decided": date_decided,
        "case_label":   case_label,
    }


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    default_output = str(
        _REPO_ROOT / "admin-tools" / "case-digest-pipeline" / "scan_results.json"
    )

    parser = argparse.ArgumentParser(description="Scan eLib for new SC cases not yet in the DB.")
    parser.add_argument(
        "--max-probe", type=int, default=400,
        help="Maximum number of IDs above the DB max to probe (default 400).",
    )
    parser.add_argument(
        "--stop-after-consecutive-misses", type=int, default=100,
        help="Stop scanning after this many consecutive blank/error IDs (default 100).",
    )
    parser.add_argument(
        "--request-delay", type=float, default=0.8,
        help="Seconds between HTTP requests (default 0.8).",
    )
    parser.add_argument(
        "--start-after", type=int, default=None,
        help="Override the last known eLib ID; first probed ID = start-after + 1.",
    )
    parser.add_argument(
        "--output", type=str, default=default_output,
        help=f"Path to write scan results JSON (default: {default_output}).",
    )
    args = parser.parse_args()

    load_api_local_settings_into_environ(_REPO_ROOT)
    db_url = os.environ.get("DB_CONNECTION_STRING")
    if not db_url:
        log.error("DB_CONNECTION_STRING is not set.")
        return 2

    conn = psycopg2.connect(db_url)
    try:
        last_case = _get_last_elib_case(conn) if args.start_after is None else {
            "elib_id":    args.start_after,
            "sc_url":     f"{ELIB_SHOWDOCS}{args.start_after}",
            "case_label": "(manual override)",
            "date":       None,
        }
        base_id = last_case["elib_id"]
    finally:
        conn.close()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    session = _session()
    scanned_at = datetime.now(timezone.utc).isoformat()
    probe_from = base_id + 1
    probe_to   = base_id + args.max_probe

    found_cases: list[dict] = []
    consecutive_misses = 0
    total_probed = 0
    stopped_reason = "max_probe_reached"

    log.info(
        "Scan starting: last DB case eLib #%s (%s)  —  next to probe: #%s",
        base_id, last_case.get('case_label') or last_case.get('sc_url'), base_id + 1,
    )
    log.info(
        "Probing eLib IDs %s … %s (max %s, stop after %s misses)",
        probe_from, probe_to, args.max_probe, args.stop_after_consecutive_misses,
    )
    print(f"""
{'='*62}
  eLib Scan — Starting Point
  Last case in DB : eLib #{base_id}
  URL             : {last_case.get('sc_url', '')}
  Case            : {last_case.get('case_label', '') or '(unknown)'}
  Next to probe   : eLib #{base_id + 1}
  Max to probe    : {args.max_probe} IDs
{'='*62}
""", flush=True)

    # Open a fresh DB connection for URL existence checks during scan
    conn = psycopg2.connect(db_url)
    try:
        for offset in range(1, args.max_probe + 1):
            elib_id = base_id + offset
            sc_url  = f"{ELIB_SHOWDOCS}{elib_id}"
            total_probed += 1

            # Quick DB existence check (cheap)
            if _url_exists(conn, sc_url):
                log.debug("Already in DB: id=%s", elib_id)
                consecutive_misses = 0
                time.sleep(0.05)  # tiny delay, not full request delay
                continue

            time.sleep(args.request_delay)
            status, snippet = _probe_page(session, elib_id)

            if status == "ok_gr":
                # Validate URL is non-empty and a real showdocs URL before recording
                if not sc_url or "/showdocs/1/" not in sc_url:
                    log.warning("[SKIP] id=%s — empty or invalid URL, skipping", elib_id)
                    consecutive_misses = 0
                    continue
                meta = _extract_case_meta(snippet, elib_id)
                found_cases.append({
                    "elib_id":      elib_id,
                    "sc_url":       sc_url,
                    "gr_number":    meta["gr_number"],
                    "date_decided": meta["date_decided"],
                    "case_label":   meta["case_label"],
                })
                consecutive_misses = 0
                log.info("[FOUND] eLib id=%s  %s", elib_id, meta["case_label"])
                # Write partial results so the UI can poll progress
                _write_results(
                    output_path, scanned_at, base_id, probe_from, elib_id,
                    total_probed, found_cases, "scanning", last_case,
                )

            elif status == "ok_not_gr":
                log.info("[SKIP] id=%s — non-G.R. docket", elib_id)
                consecutive_misses = 0

            else:
                log.debug("[MISS] id=%s (%s)", elib_id, status)
                consecutive_misses += 1
                if consecutive_misses >= args.stop_after_consecutive_misses:
                    log.info(
                        "Stopping after %s consecutive misses (last id=%s).",
                        consecutive_misses, elib_id,
                    )
                    stopped_reason = "consecutive_misses"
                    break
    finally:
        conn.close()

    # Final write
    _write_results(
        output_path, scanned_at, base_id, probe_from, probe_to,
        total_probed, found_cases, stopped_reason, last_case,
    )

    print(f"\n{'='*60}")
    print(f"  Scan complete")
    print(f"  Last DB case URL   : {last_case.get('sc_url', '')}"
          + (f" ({last_case.get('case_label')})" if last_case.get('case_label') else ""))
    print(f"  Base eLib ID in DB : {base_id}")
    print(f"  IDs probed         : {probe_from} – {base_id + total_probed}")
    print(f"  Total probed       : {total_probed}")
    print(f"  New G.R. cases     : {len(found_cases)}")
    print(f"  Stopped reason     : {stopped_reason}")
    print(f"  Results written to : {output_path}")
    print(f"{'='*60}\n")

    return 0


def _write_results(
    path: Path,
    scanned_at: str,
    base_id: int,
    probe_from: int,
    probe_to_so_far: int,
    total_probed: int,
    cases: list[dict],
    stopped_reason: str,
    last_in_db: dict | None = None,
) -> None:
    payload = {
        "scanned_at":        scanned_at,
        "max_elib_id_in_db": base_id,
        "last_in_db":        last_in_db or {},
        "probed_from":       probe_from,
        "probed_to":         probe_to_so_far,
        "total_probed":      total_probed,
        "total_new_found":   len(cases),
        "stopped_reason":    stopped_reason,
        "cases":             cases,
    }
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


if __name__ == "__main__":
    raise SystemExit(main())
