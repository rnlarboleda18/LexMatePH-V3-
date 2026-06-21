"""
classify_ratio_style.py

Classifies the digest_ratio of grok-labeled cases as 'telegraphic' or 'prose'
using Gemini 3.1 Flash-Lite exclusively via Google AI Studio.

Telegraphic = shorthand notes style: drops articles, uses abbreviations as
bridges, colon-separated citations, incomplete sentences.
Prose = full sentence legal writing.

Output CSV: scripts/ratio_style_classification.csv
  columns: id, case_number, year, style

Usage:
    python scripts/classify_ratio_style.py
    python scripts/classify_ratio_style.py --workers 20 --rpm 1000 --resume
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import psycopg2
from google import genai
from google.genai import types

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from load_local_settings_env import load_api_local_settings_into_environ

load_api_local_settings_into_environ(Path(__file__).resolve().parent.parent)

# ── Constants ────────────────────────────────────────────────────────────────

MODEL        = "gemini-3.1-flash-lite"
OUTPUT_CSV   = _SCRIPTS / "ratio_style_classification.csv"
CSV_FIELDS   = ["id", "case_number", "year", "style"]
_TIMEOUT_MS  = 60_000   # 60 s — classification is fast
_RETRY_LIMIT = 5
_RETRY_BASE  = 15       # base seconds for exponential backoff
DEFAULT_RPM  = 10       # free tier fallback quota for Google AI Studio

DB_URL = (
    os.environ.get("DB_CONNECTION_STRING_AZURE")
    or os.environ.get("DB_CONNECTION_STRING")
    or "postgres://bar_admin:RABpass021819!@lexmateph-ea-db.postgres.database.azure.com:5432/lexmateph-ea-db?sslmode=require"
)

SYSTEM_PROMPT = """\
You are a legal text style classifier. You will receive a Ratio Decidendi excerpt \
from a Philippine Supreme Court case digest.

Classify the writing style as exactly one of:
  telegraphic — shorthand note style: drops articles (the/a/an), uses abbreviations \
as inline bridges (e.g. "Sombong v. CA: Habeas in custody..."), colon-separated \
citations, parenthetical cramming, incomplete sentences, reads like structured notes
  prose       — full-sentence legal writing: complete sentences, articles present, \
proper attribution, readable as a formal legal document

Reply with a single word only: telegraphic  OR  prose
Do not explain. Do not add punctuation."""

CLASSIFY_PROMPT = """\
Classify the writing style of this Ratio Decidendi:

---
{ratio}
---

Reply with one word only: telegraphic or prose"""

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("classify_ratio_style.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# ── Token-bucket rate limiter ─────────────────────────────────────────────────

class RateLimiter:
    """Thread-safe token bucket — enforces a max requests-per-minute."""

    def __init__(self, rpm: int) -> None:
        self._interval = 60.0 / rpm   # seconds per token
        self._lock     = threading.Lock()
        self._next_allowed = time.monotonic()

    def acquire(self) -> None:
        with self._lock:
            now   = time.monotonic()
            wait  = self._next_allowed - now
            if wait > 0:
                time.sleep(wait)
            self._next_allowed = time.monotonic() + self._interval


# ── Google AI Studio client builder ─────────────────────────────────────────

def _build_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "Neither GEMINI_API_KEY nor GOOGLE_API_KEY was found in the environment. "
            "Please check that your api/local.settings.json is properly configured."
        )
    return genai.Client(
        vertexai=False,
        api_key=api_key,
        http_options={"timeout": _TIMEOUT_MS},
    )


# ── DB helpers ───────────────────────────────────────────────────────────────

def fetch_grok_cases(limit: int | None = None) -> list[dict]:
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    q = """
        SELECT id, case_number, EXTRACT(YEAR FROM date)::int AS year, digest_ratio
        FROM sc_decided_cases
        WHERE ai_model ILIKE %s
          AND digest_ratio IS NOT NULL
          AND digest_ratio <> ''
        ORDER BY date DESC
    """
    params: list = ["%grok%"]
    if limit:
        q += " LIMIT %s"
        params.append(limit)
    cur.execute(q, params)
    rows = [
        {"id": r[0], "case_number": r[1], "year": r[2], "digest_ratio": r[3]}
        for r in cur.fetchall()
    ]
    cur.close()
    conn.close()
    log.info("Fetched %d grok cases with digest_ratio.", len(rows))
    return rows


# ── CSV helpers ──────────────────────────────────────────────────────────────

def load_done_ids(csv_path: Path) -> set[int]:
    if not csv_path.exists():
        return set()
    done: set[int] = set()
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                done.add(int(row["id"]))
            except (KeyError, ValueError):
                pass
    return done


def append_row(csv_path: Path, row: dict, write_header: bool) -> None:
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerow({k: row[k] for k in CSV_FIELDS})


# ── Classification ────────────────────────────────────────────────────────────

def classify_one(client: genai.Client, limiter: RateLimiter, case: dict) -> str:
    """Returns 'telegraphic', 'prose', or 'error'."""
    prompt = CLASSIFY_PROMPT.format(ratio=case["digest_ratio"][:4000])
    for attempt in range(1, _RETRY_LIMIT + 1):
        limiter.acquire()   # block until our rate-limit slot opens
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.0,
                    max_output_tokens=50,
                ),
            )
            raw = (response.text or "").strip().lower()
            if "telegraphic" in raw:
                return "telegraphic"
            if "prose" in raw:
                return "prose"
            log.warning("Unexpected response for id=%s: %r", case["id"], raw)
            return "error"
        except Exception as exc:
            is_429 = "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc)
            log.warning("Attempt %d failed for id=%s: %s", attempt, case["id"], exc)
            if attempt < _RETRY_LIMIT:
                # Exponential backoff + jitter; longer pause on 429
                backoff = _RETRY_BASE * (2 ** (attempt - 1)) + random.uniform(0, 5)
                if is_429:
                    backoff = max(backoff, 30)   # always wait ≥30s after a 429
                log.info("Waiting %.1fs before retry %d for id=%s", backoff, attempt + 1, case["id"])
                time.sleep(backoff)
    return "error"


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Classify digest_ratio style for grok cases using Gemini 3.1 Flash-Lite on Google AI Studio."
    )
    parser.add_argument("--workers",  type=int, default=5,          help="Concurrent workers (default 5)")
    parser.add_argument("--rpm",      type=int, default=DEFAULT_RPM, help=f"Max requests/min (default {DEFAULT_RPM})")
    parser.add_argument("--limit",    type=int, default=0,           help="Max cases to process (0 = all)")
    parser.add_argument("--resume",   action="store_true",           help="Skip already-classified IDs in CSV")
    args = parser.parse_args()

    client  = _build_client()
    limiter = RateLimiter(rpm=args.rpm)
    log.info("Google AI Studio | model=%s | rpm=%d | workers=%d",
             MODEL, args.rpm, args.workers)

    cases = fetch_grok_cases(limit=args.limit or None)

    # Resume: skip already done
    done_ids: set[int] = set()
    if args.resume:
        done_ids = load_done_ids(OUTPUT_CSV)
        log.info("Resuming - %d already classified, skipping.", len(done_ids))
    pending = [c for c in cases if c["id"] not in done_ids]
    log.info("%d cases to classify.", len(pending))

    if not pending:
        log.info("Nothing to do.")
        return

    write_header = not OUTPUT_CSV.exists() or not args.resume
    counts = {"telegraphic": 0, "prose": 0, "error": 0}
    done_count = 0

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(classify_one, client, limiter, c): c for c in pending}
        for future in as_completed(futures):
            case   = futures[future]
            style  = future.result()
            counts[style] = counts.get(style, 0) + 1
            done_count += 1

            row = {
                "id":          case["id"],
                "case_number": case["case_number"],
                "year":        case["year"],
                "style":       style,
            }
            needs_header = write_header and done_count == 1
            append_row(OUTPUT_CSV, row, write_header=needs_header)

            if done_count % 500 == 0 or done_count == len(pending):
                log.info(
                    "Progress: %d/%d | telegraphic=%d prose=%d error=%d",
                    done_count, len(pending),
                    counts["telegraphic"], counts["prose"], counts["error"],
                )

    log.info("Done. Results -> %s", OUTPUT_CSV)
    log.info(
        "Final: telegraphic=%d | prose=%d | error=%d",
        counts["telegraphic"], counts["prose"], counts["error"],
    )


if __name__ == "__main__":
    main()
