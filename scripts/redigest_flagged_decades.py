"""
redigest_flagged_decades.py

Redigests (1) main_doctrine, (2) digest_issues, (3) digest_ratio, and (4) secondary_rulings
for flagged cases post-1987 in decadal-descending order, prioritizing En Banc cases first within each decade.

Uses Vertex AI exclusively (no Google AI Studio fallback) and writes strictly to the database in a non-destructive manner.

Usage:
    # Pilot run on a specific case ID (e.g., Pimentel III - 73117)
    python scripts/redigest_flagged_decades.py --id 73117 --dry-run

    # Execute a limited bulk run on 10 cases with 3 threads
    python scripts/redigest_flagged_decades.py --limit 10 --threads 3

    # Full execution
    python scripts/redigest_flagged_decades.py --threads 5 --rpm 200
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import logging
import os
import re
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
ROLE: You are a highly precise Legal Data Extraction Engine specialized in Philippine Jurisprudence for a Bar Review application. Your task is to transform raw legal text into a structured, clinical analysis for academic use.

TONE & SCOPE: Maintain a neutral, professional, and purely academic tone. Treat all descriptions of events as Case Facts or Testimony for evidentiary analysis. Do not use sensationalist language. Terminology regarding crimes is strictly for legal classification.\
"""

REDIGEST_PROMPT = """\
You are given a Philippine Supreme Court decision.

YOUR TASK: Generate and refine exactly four core digest fields for this case:
1. main_doctrine
2. digest_issues
3. digest_ratio
4. secondary_rulings

STRICT INSTRUCTIONS FOR EACH FIELD:

1. **main_doctrine**:
   - Provide a comprehensive explanation of 5-8 sentences detailing the primary legal doctrine established or applied by the Court.
   - It MUST be written strictly as a single, coherent paragraph of natural, flowing prose sentences.
   - Do NOT use any numbering, sub-bullet points, or explicit labels (such as (a), (b), (c)).
   - Clearly convey the core legal rule or holding, the constitutional, statutory, or jurisprudential rationale behind it, and its exact impact or significance for Philippine law.
   - **IMPORTANT (Conditional Guardrail):** If—and only if—the Court settled any collateral or procedural issues of major jurisprudential value in this case, you MUST explicitly mention them in a concluding sentence of this prose paragraph (e.g., 'In addition, the Court settled collateral matters concerning [issue], ruling that...'). Do NOT invent or hallucinate collateral issues if there are none.

2. **digest_issues**:
   - Provide a comprehensive, exhaustive list of ALL issues (both primary substantive issues and any and all procedural, secondary, or collateral issues) raised by the parties or addressed by the Court.
   - List every single issue using a structured markdown bullet point format. Return this as a single string.

3. **digest_ratio**:
   - Address every single issue listed in the digest_issues section (both primary and collateral/procedural) using a corresponding and clearly labeled bullet point in a point-by-point manner (e.g., '* **On Issue 1:** ...', '* **On Issue 2:** ...').
   - For each issue, write a thorough, forensic, and logically complete explanation of how the Supreme Court reasoned.
   - Provide a MINIMUM of 5-8 sentences of rigorous legal reasoning for each issue, with NO upper limit on sentence length or count to avoid truncating complex arguments.
   - Explicitly name referenced cases and statutory/constitutional provisions.

4. **secondary_rulings**:
   - Return a JSON array of objects representing collateral or secondary rulings settled by the Court that are highly relevant to Bar Exam preparation (such as procedural anomalies, quantum of proof, prospective applications, civil liability adjustments, or laches).
   - If there are no secondary or collateral rulings settled by the Court, return an empty array `[]`—do NOT invent data.
   - Each object in the array MUST have exactly these two keys:
     - **topic**: The specific legal topic (e.g., 'Procedural Due Process', 'Locus Standi', 'Double Jeopardy', 'Civil Liability in Rape').
     - **ruling**: A detailed 5-8 sentence explanation of the Court's specific pronouncement on this collateral matter, written strictly as a single, coherent paragraph of natural, flowing prose sentences. Do NOT use any numbering, sub-bullet points, or explicit labels (such as (a), (b), (c)). Ensure it is precise, authoritative, and uses the exact language of the law.

OUTPUT FORMAT:
You MUST return ONLY a valid JSON object with the following schema:
{{
    "main_doctrine": "...",
    "digest_issues": "* Issue 1\\n* Issue 2",
    "digest_ratio": "* **On Issue 1:** [5-8+ sentences of reasoning...]\\n* **On Issue 2:** [5-8+ sentences...]",
    "secondary_rulings": [
        {{"topic": "...", "ruling": "..."}}
    ]
}}

Do NOT wrap the JSON in markdown code blocks like ```json ... ```. Return ONLY the raw JSON string.

---
CASE: {case_number} — {short_title}
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

def _build_client(vertex_project: str, vertex_location: str) -> genai.Client:
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
        logging.FileHandler("redigest_flagged_decades.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# ── DB helpers ───────────────────────────────────────────────────────────────

def fetch_case(conn, case_id: int) -> dict | None:
    cur = conn.cursor()
    cur.execute(
        "SELECT id, case_number, short_title, full_text_md "
        "FROM sc_decided_cases WHERE id = %s",
        (case_id,),
    )
    row = cur.fetchone()
    cur.close()
    if not row:
        return None
    return {
        "id":           row[0],
        "case_number":  row[1],
        "short_title":  row[2],
        "full_text_md": row[3] or "",
    }


def save_digest(conn, case_id: int, main_doctrine: str, digest_issues: str, digest_ratio: str, secondary_rulings: list | dict, model: str) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE sc_decided_cases
        SET main_doctrine = %s,
            digest_issues = %s,
            digest_ratio = %s,
            secondary_rulings = %s,
            ai_model = %s,
            updated_at = NOW()
        WHERE id = %s
        """,
        (
            main_doctrine,
            digest_issues,
            digest_ratio,
            json.dumps(secondary_rulings),
            model,
            case_id,
        ),
    )
    conn.commit()
    cur.close()


# ── Generation ───────────────────────────────────────────────────────────────

def clean_json_text(text: str) -> str:
    """Strip markdown blocks or surrounding trash to get pure JSON."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def generate_digest_data(client: genai.Client, case: dict, model_name: str) -> dict | None:
    full_text = case["full_text_md"] or ""
    # Smart head-tail truncation to stay within context limits safely (~150,000 chars)
    # while preserving both the facts/history (beginning) and the critical ratio/rulings (end).
    max_chars = 150_000
    if len(full_text) > max_chars:
        head_len = int(max_chars * 0.3)  # 45,000 characters
        tail_len = max_chars - head_len  # 105,000 characters
        full_text = (
            full_text[:head_len]
            + f"\n\n[...TRUNCATED FOR LENGTH: {len(full_text) - head_len - tail_len} characters omitted between head and tail...]\n\n"
            + full_text[-tail_len:]
        )

    prompt = REDIGEST_PROMPT.format(
        case_number=case["case_number"],
        short_title=case["short_title"] or "",
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
                    response_mime_type="application/json"
                ),
            )
            text = (response.text or "").strip()
            if text:
                cleaned_text = clean_json_text(text)
                try:
                    data = json.loads(cleaned_text)
                    # Verify required fields
                    required_keys = {"main_doctrine", "digest_issues", "digest_ratio", "secondary_rulings"}
                    if all(k in data for k in required_keys):
                        return data
                    log.warning("Missing keys in JSON for id=%s on attempt %d: %s", case["id"], attempt, data.keys())
                except json.JSONDecodeError as jde:
                    log.warning("JSON decode failed for id=%s on attempt %d: %s\nText: %s", case["id"], attempt, jde, text[:200])
            else:
                log.warning("Empty response on attempt %d for id=%s", attempt, case["id"])
        except Exception as exc:
            log.warning("Attempt %d failed for id=%s: %s", attempt, case["id"], exc)
            if attempt < _RETRY_LIMIT:
                time.sleep(_RETRY_DELAY * attempt)
    return None


# ── Process Case ─────────────────────────────────────────────────────────────

def process_case(
    client: genai.Client,
    conn,
    db_lock: threading.Lock,
    case_id: int,
    dry_run: bool,
    model_name: str,
    limiter: RateLimiter | None
) -> bool:
    with db_lock:
        case = fetch_case(conn, case_id)

    if not case:
        log.error("Case id=%s not found in database", case_id)
        return False

    log.info("Starting Case ID %d: %s — %s (Size: %d chars)", case["id"], case["case_number"], case["short_title"], len(case["full_text_md"]))

    if limiter:
        limiter.acquire()

    data = generate_digest_data(client, case, model_name)
    if not data:
        log.error("Generation failed for Case ID %d", case_id)
        return False

    if dry_run:
        log.info("DRY RUN for Case ID %d. Extracted fields:", case_id)
        log.info("Main Doctrine:\n%s", data["main_doctrine"])
        log.info("Digest Issues:\n%s", data["digest_issues"])
        log.info("Digest Ratio:\n%s", data["digest_ratio"])
        log.info("Secondary Rulings:\n%s", json.dumps(data["secondary_rulings"], indent=2))
        return True

    with db_lock:
        try:
            save_digest(
                conn,
                case_id,
                data["main_doctrine"],
                data["digest_issues"],
                data["digest_ratio"],
                data["secondary_rulings"],
                model_name
            )
            log.info("Successfully updated Case ID %d", case_id)
            return True
        except Exception as e:
            log.error("Database save failed for Case ID %d: %s", case_id, e)
            conn.rollback()
            return False


# ── Decadal Runner ───────────────────────────────────────────────────────────

def load_case_list(decadal_split_path: Path) -> list[int]:
    """Loads all IDs descending by decade and En Banc first within each decade."""
    with open(decadal_split_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    ordered_ids = []
    # Order of decades descending
    decades = ["2020-2026", "2010-2019", "2000-2009", "1987-1999"]
    for dec in decades:
        if dec in data:
            group = data[dec]
            eb_ids = group.get("eb_ids", [])
            div_ids = group.get("div_ids", [])
            log.info("Decade %s: Found %d En Banc, %d Division cases", dec, len(eb_ids), len(div_ids))
            ordered_ids.extend(eb_ids)
            ordered_ids.extend(div_ids)

    return ordered_ids


def main() -> None:
    parser = argparse.ArgumentParser(description="Redigest core case fields post-1987 in decadal-descending order.")
    parser.add_index = parser.add_argument  # convenience
    parser.add_argument("--id", type=int, help="Run only on a specific case ID")
    parser.add_argument("--limit", type=int, help="Max cases to process")
    parser.add_argument("--threads", type=int, default=5, help="Number of worker threads")
    parser.add_argument("--rpm", type=int, default=200, help="Vertex AI RPM rate limit")
    parser.add_argument("--dry-run", action="store_true", help="Print updates, do not write to DB")
    parser.add_argument("--model", default=MODEL, help="Vertex AI Gemini model")
    parser.add_argument("--vertex-project", default=DEFAULT_PROJECT, help="Vertex AI project name")
    parser.add_argument("--vertex-location", default=DEFAULT_LOCATION, help="Vertex AI location")
    parser.add_argument("--split-file", help="Path to decadal_split.json")
    args = parser.parse_args()

    # Find split file path
    split_path = None
    if args.split_file:
        split_path = Path(args.split_file)
    else:
        # Check standard locations
        possible_paths = [
            _SCRIPTS.parent / "scratch" / "decadal_split.json",
            Path("C:/Users/rnlar/.gemini/antigravity/brain/ac8796fd-0d6a-4d86-bb3e-30e75fc2ba03/scratch/decadal_split.json"),
            _SCRIPTS / "decadal_split.json"
        ]
        for p in possible_paths:
            if p.is_file():
                split_path = p
                break

    if not args.id and (not split_path or not split_path.is_file()):
        print(f"Error: decadal_split.json not found. Looked in {[str(p) for p in possible_paths]}", file=sys.stderr)
        sys.exit(1)

    print(f"Database URL: {DB_URL.split('@')[-1] if '@' in DB_URL else DB_URL}")
    print(f"Vertex Project: {args.vertex_project}")
    print(f"Vertex Model: {args.model}")

    try:
        conn = psycopg2.connect(DB_URL)
    except Exception as e:
        print(f"Failed to connect to database: {e}", file=sys.stderr)
        sys.exit(1)

    db_lock = threading.Lock()
    limiter = RateLimiter(args.rpm) if args.rpm > 0 else None

    # Load targets
    if args.id:
        targets = [args.id]
        print(f"Targeting specific Case ID: {args.id}")
    else:
        print(f"Loading cases from {split_path}")
        targets = load_case_list(split_path)
        print(f"Total targeted cases: {len(targets)}")

    if args.limit:
        targets = targets[:args.limit]
        print(f"Limited to first {args.limit} cases")

    if not targets:
        print("No cases to process. Exiting.")
        sys.exit(0)

    # Initialize client
    try:
        client = _build_client(args.vertex_project, args.vertex_location)
    except Exception as e:
        print(f"Failed to build Vertex AI client: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Processing with {args.threads} threads...")
    success_count = 0
    failure_count = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = {
            executor.submit(
                process_case,
                client,
                conn,
                db_lock,
                case_id,
                args.dry_run,
                args.model,
                limiter
            ): case_id
            for case_id in targets
        }

        for fut in concurrent.futures.as_completed(futures):
            case_id = futures[fut]
            try:
                success = fut.result()
                if success:
                    success_count += 1
                else:
                    failure_count += 1
            except Exception as e:
                log.exception("Unexpected exception processing Case ID %d: %s", case_id, e)
                failure_count += 1

    conn.close()
    print("\n--- RUN COMPLETE ---")
    print(f"Successful digests: {success_count}")
    print(f"Failed digests: {failure_count}")


if __name__ == "__main__":
    main()
