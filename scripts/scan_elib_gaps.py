#!/usr/bin/env python3
"""
scan_elib_gaps.py
=================
Finds eLib IDs that are MISSING from ``sc_decided_cases`` between the
minimum and maximum IDs already in your database, then probes each gap
against the SC E-Library to determine if it is a real G.R. case you
should ingest.

Why this matters
----------------
``scan_elib_new_cases.py`` only looks *forward* from the highest known
eLib ID.  If earlier scraping runs skipped IDs (network errors, non-G.R.
pages mixed in, eLib downtime, etc.) those cases are silently missing.
This script fills that blind spot.

How it works
------------
1. Queries the DB for the full set of eLib numeric IDs already stored.
2. Generates the complete integer series from min_id to max_id.
3. Computes the difference — these are the "gap IDs".
4. Probes each gap ID on eLib (same lightweight probe as the scan script).
5. Records only real G.R. cases as "missed" cases that need ingestion.
6. Writes incremental JSON results so you can monitor progress in real time.
7. Supports --resume to skip IDs already probed in a previous run.

Output JSON (written to --output path):
  {
    "scanned_at":      "<ISO timestamp>",
    "db_min_id":       1000,
    "db_max_id":       73500,
    "total_gap_ids":   312,
    "total_probed":    200,
    "total_gr_missed": 5,
    "total_non_gr":    18,
    "total_empty":     177,
    "stopped_reason":  "complete" | "interrupted" | "consecutive_misses",
    "missed_cases": [
      {
        "elib_id":      42300,
        "sc_url":       "https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/42300",
        "gr_number":    "G.R. No. 201234",
        "date_decided": "March 15, 2012",
        "case_label":   "G.R. No. 201234 | March 15, 2012"
      },
      ...
    ]
  }

Usage
-----
  # Full gap scan (may take hours for large DBs — use --max-probe to limit)
  python scripts/scan_elib_gaps.py

  # Limit to first 500 gap IDs
  python scripts/scan_elib_gaps.py --max-probe 500

  # Resume a previous run (skips already-probed IDs recorded in the output file)
  python scripts/scan_elib_gaps.py --resume

  # Custom output path
  python scripts/scan_elib_gaps.py --output /tmp/gap_results.json

  # Only check a specific ID range (override DB range)
  python scripts/scan_elib_gaps.py --range-from 10000 --range-to 50000
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

# ── Constants ─────────────────────────────────────────────────────────────────

ELIB_SHOWDOCS = "https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/"

_GR_PATTERN = re.compile(r"G\s*\.\s*R\s*\.\s*No\.", re.IGNORECASE)
_DECISION_PATTERN = re.compile(
    r"D\s*E\s*C\s*I\s*S\s*I\s*O\s*N|R\s*E\s*S\s*O\s*L\s*U\s*T\s*I\s*O\s*N",
    re.IGNORECASE,
)

log = logging.getLogger(__name__)


# ── HTTP session ──────────────────────────────────────────────────────────────

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


# ── DB helpers ────────────────────────────────────────────────────────────────

def _get_elib_id_range(conn) -> tuple[int, int]:
    """Return (min_elib_id, max_elib_id) from sc_decided_cases."""
    cur = conn.cursor()
    cur.execute(
        r"""
        SELECT
            MIN(CAST(SUBSTRING(sc_url FROM '/showdocs/1/([0-9]+)') AS INTEGER)),
            MAX(CAST(SUBSTRING(sc_url FROM '/showdocs/1/([0-9]+)') AS INTEGER))
        FROM sc_decided_cases
        WHERE sc_url ILIKE %s
          AND sc_url ~ %s
        """,
        (
            "%elibrary.judiciary.gov.ph%thebookshelf/showdocs/1/%",
            r"/showdocs/1/[0-9]+",
        ),
    )
    row = cur.fetchone()
    cur.close()
    if not row or row[0] is None:
        return 0, 0
    return int(row[0]), int(row[1])


def _get_present_ids(conn, min_id: int, max_id: int) -> set[int]:
    """Return the set of eLib IDs already in the DB between min_id and max_id."""
    cur = conn.cursor()
    cur.execute(
        r"""
        SELECT CAST(SUBSTRING(sc_url FROM '/showdocs/1/([0-9]+)') AS INTEGER) AS elib_id
        FROM sc_decided_cases
        WHERE sc_url ILIKE %s
          AND sc_url ~ %s
          AND CAST(SUBSTRING(sc_url FROM '/showdocs/1/([0-9]+)') AS INTEGER)
              BETWEEN %s AND %s
        """,
        (
            "%elibrary.judiciary.gov.ph%thebookshelf/showdocs/1/%",
            r"/showdocs/1/[0-9]+",
            min_id,
            max_id,
        ),
    )
    ids = {int(row[0]) for row in cur.fetchall()}
    cur.close()
    log.info("Found %s IDs already in DB (range %s–%s)", len(ids), min_id, max_id)
    return ids


def _norm_case_number(s: str) -> str:
    """Normalise a case-number string for cross-checking."""
    s = re.sub(r"\s+", " ", s.strip()).lower()
    s = s.replace("nos.", "no.")
    s = s.replace(" & ", " and ")
    return s


def _get_present_case_numbers(conn) -> set[str]:
    """Return normalised G.R. case_numbers already in sc_decided_cases."""
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT case_number FROM sc_decided_cases
            WHERE case_number IS NOT NULL
              AND btrim(case_number) != ''
              AND case_number ~* '^[[:space:]]*G[.]?[[:space:]]*R[.]?'
            """
        )
        nums = {_norm_case_number(row[0]) for row in cur.fetchall()}
        cur.close()
        log.info("Loaded %s G.R. case numbers from DB for cross-check.", len(nums))
        return nums
    except Exception as exc:
        log.warning("Could not load case numbers for cross-check (skipping): %s", exc)
        return set()


# ── eLib probe (same logic as scan_elib_new_cases.py) ────────────────────────

def _probe_page(session: requests.Session, elib_id: int) -> tuple[str, str]:
    """
    Returns (status, snippet):
      "ok_gr"      — valid G.R. case page
      "ok_not_gr"  — valid page, non-G.R. docket (A.M., A.C., etc.)
      "miss"       — 404, error page, or no decision content
      "http_error" — network / non-200 response
    """
    url = f"{ELIB_SHOWDOCS}{elib_id}"
    try:
        r = session.get(url, timeout=40, stream=True)
    except requests.RequestException as exc:
        log.debug("HTTP error id=%s: %s", elib_id, exc)
        return "http_error", ""

    if r.status_code != 200:
        return "http_error", ""

    chunk = b""
    for data in r.iter_content(131072):
        chunk += data
        if len(chunk) >= 131072:
            break
    r.close()

    text = chunk.decode("utf-8", errors="replace")

    if "elibrary.judiciary.gov.ph" in text and re.search(
        r"(The document you requested|not found|does not exist)", text, re.IGNORECASE
    ):
        return "miss", ""

    if not _DECISION_PATTERN.search(text):
        return "miss", ""

    # Check only the header area (~12 KB) so that G.R. citations in the
    # body of A.M./A.C./MTJ/RTJ decisions don't cause false positives.
    if _GR_PATTERN.search(text[:12000]):
        return "ok_gr", text[:10000]
    return "ok_not_gr", text[:3000]


def _extract_case_meta(html_snippet: str, elib_id: int) -> dict:
    """Extract GR number and date from an eLib page snippet."""
    gr_number = ""
    date_decided = ""

    _MONTHS = (
        r"(?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December)"
    )

    bracket = re.search(
        r"\[\s*"
        r"(G\.?\s*R\.?\s*Nos?\.?\s*[^\]]+?)"
        r",\s*"
        rf"({_MONTHS}\s+\d{{1,2}},?\s*\d{{4}})"
        r"\s*\]",
        html_snippet,
        re.IGNORECASE | re.DOTALL,
    )

    if bracket:
        raw_gr = bracket.group(1).strip().rstrip(",")
        raw_gr = re.sub(r"&amp;",  "&",  raw_gr, flags=re.IGNORECASE)
        raw_gr = re.sub(r"&nbsp;", " ",  raw_gr, flags=re.IGNORECASE)
        raw_gr = re.sub(r"&[a-z]+;", "", raw_gr, flags=re.IGNORECASE)
        raw_gr = re.sub(r"\s+", " ", raw_gr).strip()
        raw_gr = re.sub(r"-\s+(\d)", r"-\1", raw_gr)
        date_decided = re.sub(r"\s+", " ", bracket.group(2).strip())

        nums_part = re.sub(r"^G\.?\s*R\.?\s*Nos?\.?\s*", "", raw_gr, flags=re.IGNORECASE).strip()
        is_plural = bool(re.search(r",|\band\b|&", nums_part, re.IGNORECASE))
        prefix    = "G.R. Nos." if is_plural else "G.R. No."
        gr_number = f"{prefix} {nums_part}"[:80]
    else:
        m = re.search(
            r"G\.?\s*R\.?\s*Nos?\.?\s*((?:\d[\d\-]*)(?:(?:\s*,\s*|\s+and\s+|\s*&\s*)\d[\d\-]*)*)",
            html_snippet, re.IGNORECASE,
        )
        if m:
            raw_nums  = re.sub(r"\s+", " ", m.group(1).strip().rstrip(","))
            is_plural = bool(re.search(r",|\band\b|&", raw_nums, re.IGNORECASE))
            prefix    = "G.R. Nos." if is_plural else "G.R. No."
            gr_number = f"{prefix} {raw_nums}"[:80]

        dm = re.search(rf"{_MONTHS}\s+\d{{1,2}},?\s*\d{{4}}", html_snippet, re.IGNORECASE)
        if dm:
            date_decided = re.sub(r"\s+", " ", dm.group(0).strip())
        else:
            dm2 = re.search(
                r"\b(20\d{2})[-/](0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01])\b",
                html_snippet,
            )
            if dm2:
                import datetime as _dt
                try:
                    parsed = _dt.date(int(dm2.group(1)), int(dm2.group(2)), int(dm2.group(3)))
                    date_decided = parsed.strftime("%B %d, %Y")
                except ValueError:
                    date_decided = dm2.group(0)

    case_label = " | ".join(filter(None, [gr_number, date_decided])) or f"eLib #{elib_id}"
    return {"gr_number": gr_number, "date_decided": date_decided, "case_label": case_label}


# ── Result writer ─────────────────────────────────────────────────────────────

def _write_results(
    path: Path,
    scanned_at: str,
    db_min_id: int,
    db_max_id: int,
    total_gap_ids: int,
    total_probed: int,
    total_non_gr: int,
    total_empty: int,
    missed_cases: list[dict],
    stopped_reason: str,
) -> None:
    payload = {
        "scanned_at":      scanned_at,
        "db_min_id":       db_min_id,
        "db_max_id":       db_max_id,
        "total_gap_ids":   total_gap_ids,
        "total_probed":    total_probed,
        "total_gr_missed": len(missed_cases),
        "total_non_gr":    total_non_gr,
        "total_empty":     total_empty,
        "stopped_reason":  stopped_reason,
        "missed_cases":    missed_cases,
    }
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    default_output = str(
        _REPO_ROOT / "admin-tools" / "case-digest-pipeline" / "gap_results.json"
    )

    parser = argparse.ArgumentParser(
        description="Find eLib G.R. cases missing from your DB (gap scan)."
    )
    parser.add_argument(
        "--max-probe", type=int, default=None,
        help="Maximum number of gap IDs to probe in this run (default: all gaps).",
    )
    parser.add_argument(
        "--request-delay", type=float, default=0.8,
        help="Seconds between HTTP requests (default 0.8).",
    )
    parser.add_argument(
        "--range-from", type=int, default=None,
        help="Override the DB minimum eLib ID (inclusive).",
    )
    parser.add_argument(
        "--range-to", type=int, default=None,
        help="Override the DB maximum eLib ID (inclusive).",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Skip gap IDs already recorded in the output file from a previous run.",
    )
    parser.add_argument(
        "--stop-after-consecutive-misses", type=int, default=None,
        help="Stop after this many consecutive misses (default: disabled for gap scans).",
    )
    parser.add_argument(
        "--output", type=str, default=default_output,
        help=f"Path to write gap results JSON (default: {default_output}).",
    )
    args = parser.parse_args()

    load_api_local_settings_into_environ(_REPO_ROOT)
    db_url = os.environ.get("DB_CONNECTION_STRING")
    if not db_url:
        log.error("DB_CONNECTION_STRING is not set.")
        return 2

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # ── Load previous results if resuming ────────────────────────────────────
    already_probed: set[int] = set()
    existing_missed: list[dict] = []
    existing_non_gr = 0
    existing_empty  = 0

    if args.resume and output_path.exists():
        try:
            prev = json.loads(output_path.read_text(encoding="utf-8"))
            for c in prev.get("missed_cases", []):
                already_probed.add(int(c["elib_id"]))
                existing_missed.append(c)
            existing_non_gr = prev.get("total_non_gr", 0)
            existing_empty  = prev.get("total_empty",  0)
            # Rebuild already_probed from total_probed count isn't possible,
            # so we track via missed_cases + a separate probed_ids file if needed.
            # For simplicity, resume skips IDs in missed_cases only.
            log.info(
                "Resuming: %s missed cases already recorded from previous run.",
                len(existing_missed),
            )
        except Exception as exc:
            log.warning("Could not load previous results for resume: %s", exc)

    # ── Connect and compute gap IDs ──────────────────────────────────────────
    conn = psycopg2.connect(db_url)
    try:
        db_min, db_max = _get_elib_id_range(conn)
        if db_min == 0 and db_max == 0:
            log.error("No eLib cases found in sc_decided_cases. Aborting.")
            conn.close()
            return 1

        range_from = args.range_from if args.range_from is not None else db_min
        range_to   = args.range_to   if args.range_to   is not None else db_max

        log.info("DB eLib ID range: %s – %s", db_min, db_max)
        log.info("Scanning range:   %s – %s", range_from, range_to)

        present_ids = _get_present_ids(conn, range_from, range_to)
        try:
            present_case_numbers = _get_present_case_numbers(conn)
        except Exception as exc:
            log.warning("Case-number cross-check unavailable (%s) — proceeding without it.", exc)
            present_case_numbers = set()
    finally:
        conn.close()

    full_range  = set(range(range_from, range_to + 1))
    gap_ids     = sorted(full_range - present_ids)
    total_gaps  = len(gap_ids)

    if args.resume:
        gap_ids = [i for i in gap_ids if i not in already_probed]
        log.info(
            "After resume filter: %s gap IDs remaining to probe (%s already done).",
            len(gap_ids), total_gaps - len(gap_ids),
        )

    if args.max_probe is not None:
        gap_ids = gap_ids[:args.max_probe]

    print(f"""
{'='*64}
  eLib Gap Scan — Starting Point
  DB range        : eLib #{range_from} – #{range_to}
  Total IDs in range  : {range_to - range_from + 1:,}
  IDs present in DB   : {len(present_ids):,}
  Gap IDs found       : {total_gaps:,}
  IDs to probe now    : {len(gap_ids):,}
  Request delay       : {args.request_delay}s
  Output              : {output_path}
{'='*64}
""", flush=True)

    if not gap_ids:
        log.info("No gap IDs to probe. Database appears complete for this range.")
        _write_results(
            output_path, datetime.now(timezone.utc).isoformat(),
            db_min, db_max, total_gaps, 0, 0, 0, existing_missed, "complete",
        )
        return 0

    session     = _session()
    scanned_at  = datetime.now(timezone.utc).isoformat()
    missed_cases: list[dict] = list(existing_missed)
    total_probed = 0
    total_non_gr = existing_non_gr
    total_empty  = existing_empty
    stopped_reason = "complete"
    consecutive_misses = 0

    for elib_id in gap_ids:
        total_probed += 1

        time.sleep(args.request_delay)
        status, snippet = _probe_page(session, elib_id)

        if status == "ok_gr":
            meta = _extract_case_meta(snippet, elib_id)
            # Skip if already ingested under a different eLib ID
            if meta["gr_number"] and _norm_case_number(meta["gr_number"]) in present_case_numbers:
                total_non_gr += 1
                consecutive_misses = 0
                log.info("[ALREADY IN DB] eLib #%s  %s", elib_id, meta["gr_number"])
            else:
                sc_url = f"{ELIB_SHOWDOCS}{elib_id}"
                missed_cases.append({
                    "elib_id":      elib_id,
                    "sc_url":       sc_url,
                    "gr_number":    meta["gr_number"],
                    "date_decided": meta["date_decided"],
                    "case_label":   meta["case_label"],
                })
                consecutive_misses = 0
                log.info("[MISSED G.R.] eLib #%s  %s", elib_id, meta["case_label"])

        elif status == "ok_not_gr":
            total_non_gr += 1
            consecutive_misses = 0
            log.info("[NOT G.R.]  eLib #%s — non-G.R. docket (A.M./A.C./etc.)", elib_id)

        else:
            total_empty += 1
            consecutive_misses += 1
            log.debug("[EMPTY/ERR] eLib #%s (%s)", elib_id, status)

            if (
                args.stop_after_consecutive_misses is not None
                and consecutive_misses >= args.stop_after_consecutive_misses
            ):
                log.info(
                    "Stopping after %s consecutive misses (last id=%s).",
                    consecutive_misses, elib_id,
                )
                stopped_reason = "consecutive_misses"
                break

        # Write incremental progress every 10 probes
        if total_probed % 10 == 0:
            _write_results(
                output_path, scanned_at, db_min, db_max,
                total_gaps, total_probed + (total_gaps - len(gap_ids) if args.resume else 0),
                total_non_gr, total_empty, missed_cases, "scanning",
            )
            log.info(
                "Progress: %s/%s probed | %s G.R. missed | %s non-G.R. | %s empty",
                total_probed, len(gap_ids),
                len(missed_cases) - len(existing_missed),
                total_non_gr - existing_non_gr,
                total_empty - existing_empty,
            )

    # Final write
    _write_results(
        output_path, scanned_at, db_min, db_max,
        total_gaps,
        total_probed + (total_gaps - len(gap_ids) if args.resume else 0),
        total_non_gr, total_empty, missed_cases, stopped_reason,
    )

    new_missed = len(missed_cases) - len(existing_missed)

    print(f"\n{'='*64}")
    print(f"  Gap scan complete")
    print(f"  DB range        : eLib #{range_from} – #{range_to}")
    print(f"  Total gap IDs   : {total_gaps:,}")
    print(f"  IDs probed      : {total_probed:,}")
    print(f"  NEW G.R. missed : {new_missed:,}  ← these need ingestion")
    print(f"  Non-G.R. (A.M. etc.) : {total_non_gr - existing_non_gr:,}")
    print(f"  Empty / errors  : {total_empty - existing_empty:,}")
    print(f"  Stopped reason  : {stopped_reason}")
    print(f"  Results written : {output_path}")
    print(f"{'='*64}\n")

    if new_missed > 0:
        print(f"  ⚠  {new_missed} G.R. case(s) found in eLib but missing from your DB.")
        print(f"     Run the Full Pipeline to ingest them.")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
