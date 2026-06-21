"""
redigest_ratio_only.py

Redigests ONLY the digest_ratio field for one or more cases using
Gemini 2.5 Flash on Vertex AI exclusively (no Google AI Studio fallback).

Intended for telegraphic-style ratios identified by classify_ratio_style.py.
Reads full_text_md + existing digest_issues as context, generates fresh
prose-style ratio, and overwrites digest_ratio + updates ai_model.

Usage:
    # Single case by GR number
    python scripts/redigest_ratio_only.py --case-number "G.R. No. 218543"

    # Single case by DB id
    python scripts/redigest_ratio_only.py --id 72597

    # Dry run — print generated ratio, don't save
    python scripts/redigest_ratio_only.py --case-number "G.R. No. 218543" --dry-run

    # Bulk: feed a CSV of ids (from classify_ratio_style.py output)
    python scripts/redigest_ratio_only.py --from-csv scripts/ratio_style_classification.csv

    # Vertex project override
    python scripts/redigest_ratio_only.py --case-number "G.R. No. 218543" --vertex-project gen-lang-client-0813708151
"""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import logging
import os
import sys
import threading
import time
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

MODEL            = "gemini-2.5-flash"
DEFAULT_PROJECT  = "gen-lang-client-0813708151"
DEFAULT_LOCATION = "us-central1"
_TIMEOUT_MS      = 270_000
_RETRY_LIMIT     = 3
_RETRY_DELAY     = 8

DB_URL = (
    os.environ.get("DB_CONNECTION_STRING_AZURE")
    or os.environ.get("DB_CONNECTION_STRING")
    or "postgres://bar_admin:RABpass021819!@lexmateph-ea-db.postgres.database.azure.com:5432/lexmateph-ea-db?sslmode=require"
)

SYSTEM_INSTRUCTION = """\
ROLE: You are a highly precise Legal Data Extraction Engine specialized in \
Philippine Jurisprudence for a Bar Review application. Your task is to write \
a Ratio Decidendi section from raw legal text in full-sentence academic prose.

TONE & SCOPE: Maintain a neutral, professional, and purely academic tone. \
Treat all descriptions of events as Case Facts or Testimony for evidentiary \
analysis. Do not use sensationalist language. Terminology regarding crimes \
is strictly for legal classification."""

RATIO_PROMPT = """\
You are given a Philippine Supreme Court decision and its existing list of issues.

YOUR TASK: Write ONLY the Ratio Decidendi (the court's legal reasoning) for this case.

STRICT FORMATTING RULES:
1. Use one bullet point per issue: * **On [Issue Label]:** [full reasoning]
2. Each bullet MUST contain 5 or more complete sentences in academic prose.
3. DO NOT use shorthand, telegraphic notes, or abbreviations without first \
defining them in full (e.g. write "Court of Appeals (CA)" on first use, then "CA" after).
4. DO NOT drop articles (the, a, an). Write in full sentences as you would in a \
formal legal brief.
5. Every issue in the ISSUES section below MUST have a corresponding bullet point.
6. All reasoning for one issue stays in one bullet. Do NOT split into sub-bullets \
labeled "Continued" or similar.
7. Cite cases by name; do not invent citations.

OUTPUT: Return ONLY the ratio text as a Markdown string. No JSON. No preamble. \
No explanation. Start directly with the first bullet point.

---
CASE: {case_number} — {short_title}
---
ISSUES:
{issues}
---
FULL DECISION TEXT:
{full_text}
"""


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


# ── Client builder ───────────────────────────────────────────────────────────

def _build_client(studio: bool, vertex_project: str, vertex_location: str) -> genai.Client:
    if studio:
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
    else:
        # Strip any AI Studio env vars to prevent SDK from silently rerouting
        for var in ("GOOGLE_API_KEY", "GEMINI_API_KEY", "GOOGLE_GENAI_USE_VERTEXAI"):
            os.environ.pop(var, None)
        return genai.Client(
            vertexai=True,
            project=vertex_project,
            location=vertex_location,
            http_options={"timeout": _TIMEOUT_MS},
        )


# ── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("redigest_ratio_only.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# ── DB helpers ───────────────────────────────────────────────────────────────

def fetch_case(conn, *, case_id: int | None = None, case_number: str | None = None) -> dict | None:
    cur = conn.cursor()
    if case_id:
        cur.execute(
            "SELECT id, case_number, short_title, digest_issues, full_text_md "
            "FROM sc_decided_cases WHERE id = %s",
            (case_id,),
        )
    else:
        cur.execute(
            "SELECT id, case_number, short_title, digest_issues, full_text_md "
            "FROM sc_decided_cases WHERE case_number ILIKE %s",
            (f"%{case_number}%",),
        )
    row = cur.fetchone()
    cur.close()
    if not row:
        return None
    return {
        "id":           row[0],
        "case_number":  row[1],
        "short_title":  row[2],
        "digest_issues": row[3] or "",
        "full_text_md": row[4] or "",
    }


def save_ratio(conn, case_id: int, ratio: str, model: str) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE sc_decided_cases
        SET digest_ratio = %s,
            ai_model     = %s,
            updated_at   = NOW()
        WHERE id = %s
        """,
        (ratio, model, case_id),
    )
    conn.commit()
    cur.close()


# ── Generation ───────────────────────────────────────────────────────────────

def generate_ratio(client: genai.Client, case: dict, model_name: str) -> str | None:
    full_text = case["full_text_md"]

    prompt = RATIO_PROMPT.format(
        case_number=case["case_number"],
        short_title=case["short_title"] or "",
        issues=case["digest_issues"] or "(no existing issues — infer from text)",
        full_text=full_text,
    )

    safety = [
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
    ]

    for attempt in range(1, _RETRY_LIMIT + 1):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.1,
                    safety_settings=safety,
                ),
            )
            text = (response.text or "").strip()
            if text:
                return text
            log.warning("Empty response on attempt %d for id=%s", attempt, case["id"])
        except Exception as exc:
            log.warning("Attempt %d failed for id=%s: %s", attempt, case["id"], exc)
            if attempt < _RETRY_LIMIT:
                time.sleep(_RETRY_DELAY * attempt)
    return None


# ── Main ──────────────────────────────────────────────────────────────────────

def process_case(
    client: genai.Client,
    conn,
    db_lock: threading.Lock,
    case_id: int | None,
    case_number: str | None,
    dry_run: bool,
    model_name: str,
    resume: bool,
    limiter: RateLimiter | None
) -> bool:
    with db_lock:
        if resume and case_id:
            cur = conn.cursor()
            cur.execute("SELECT ai_model, digest_ratio FROM sc_decided_cases WHERE id = %s", (case_id,))
            row = cur.fetchone()
            cur.close()
            if row:
                existing_model, existing_ratio = row
                if existing_model == model_name and existing_ratio:
                    log.info("Skipping id=%s (already redigested with %s)", case_id, model_name)
                    return True

        case = fetch_case(conn, case_id=case_id, case_number=case_number)

    if not case:
        log.error("Case not found: id=%s number=%s", case_id, case_number)
        return False

    log.info("Processing %s — %s (id=%s)", case["case_number"], case["short_title"], case["id"])

    if not case["full_text_md"]:
        log.error("No full_text_md for id=%s — cannot redigest.", case["id"])
        return False

    if limiter:
        limiter.acquire()

    ratio = generate_ratio(client, case, model_name)
    if not ratio:
        log.error("Failed to generate ratio for id=%s", case["id"])
        return False

    log.info("Generated ratio (%d chars) for id=%s", len(ratio), case["id"])

    if dry_run:
        print("\n" + "=" * 80)
        print(f"DRY RUN — {case['case_number']}")
        print("=" * 80)
        print(ratio)
        print("=" * 80 + "\n")
        return True

    with db_lock:
        save_ratio(conn, case["id"], ratio, model_name)
    log.info("Saved digest_ratio for id=%s, ai_model=%s", case["id"], model_name)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Redigest digest_ratio only via Vertex AI or Google AI Studio.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--case-number", help='GR number, e.g. "G.R. No. 218543"')
    group.add_argument("--id", type=int, help="DB row id")
    group.add_argument("--from-csv", help="CSV from classify_ratio_style.py (telegraphic rows only)")

    parser.add_argument("--studio", action="store_true", help="Use Google AI Studio instead of Vertex AI")
    parser.add_argument("--model", default=MODEL, help="Model name to use (default: gemini-2.5-flash)")
    parser.add_argument("--workers", type=int, default=1, help="Number of parallel worker threads (default: 1)")
    parser.add_argument("--rpm", type=int, default=1000, help="Max requests per minute limit (default: 1000)")
    parser.add_argument("--resume", action="store_true", help="Skip cases already redigested with the target model")

    parser.add_argument("--vertex-project",  default=DEFAULT_PROJECT)
    parser.add_argument("--vertex-location", default=DEFAULT_LOCATION)
    parser.add_argument("--dry-run", action="store_true", help="Print ratio, do not save to DB")
    args = parser.parse_args()

    client = _build_client(args.studio, args.vertex_project, args.vertex_location)
    if args.studio:
        log.info("Google AI Studio | model=%s", args.model)
    else:
        log.info("Vertex AI | project=%s | location=%s | model=%s",
                 args.vertex_project, args.vertex_location, args.model)

    conn = psycopg2.connect(DB_URL)
    db_lock = threading.Lock()
    limiter = RateLimiter(args.rpm) if args.rpm > 0 else None

    if args.from_csv:
        csv_path = Path(args.from_csv)
        if not csv_path.exists():
            log.error("CSV not found: %s", csv_path)
            sys.exit(1)
        ids: list[int] = []
        with csv_path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("style", "").strip().lower() == "telegraphic":
                    try:
                        ids.append(int(row["id"]))
                    except (KeyError, ValueError):
                        pass
        log.info("CSV: %d telegraphic cases to redigest.", len(ids))

        ok = fail = 0
        if args.workers > 1:
            log.info("Using ThreadPoolExecutor with %d workers.", args.workers)
            with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
                futures = {
                    executor.submit(
                        process_case,
                        client,
                        conn,
                        db_lock,
                        cid,
                        None,
                        args.dry_run,
                        args.model,
                        args.resume,
                        limiter,
                    ): cid
                    for cid in ids
                }
                for future in concurrent.futures.as_completed(futures):
                    cid = futures[future]
                    try:
                        success = future.result()
                        if success:
                            ok += 1
                        else:
                            fail += 1
                    except Exception as e:
                        log.error("Thread raised exception for id=%s: %s", cid, e)
                        fail += 1
        else:
            for cid in ids:
                success = process_case(
                    client,
                    conn,
                    db_lock,
                    cid,
                    None,
                    args.dry_run,
                    args.model,
                    args.resume,
                    limiter,
                )
                if success:
                    ok += 1
                else:
                    fail += 1
        log.info("Done. ok=%d fail=%d", ok, fail)
    else:
        process_case(
            client,
            conn,
            db_lock,
            args.id,
            args.case_number,
            args.dry_run,
            args.model,
            args.resume,
            limiter,
        )

    conn.close()


if __name__ == "__main__":
    main()
