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
import subprocess
from google import genai
from google.genai import types

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from load_local_settings_env import load_api_local_settings_into_environ

load_api_local_settings_into_environ(Path(__file__).resolve().parent.parent)

# ── Constants ────────────────────────────────────────────────────────────────

MODEL            = "publishers/google/models/gemini-3.5-flash"
DEFAULT_PROJECT  = "project-0c3350f3-e867-449e-8f7"
DEFAULT_LOCATION = "us"
DEFAULT_THREADS  = 5
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
   You are acting as a Philippine Bar Exam coach. Scan the ENTIRE decision text with forensic precision and extract EVERY secondary, collateral, or incidental legal ruling that the Court settled beyond the primary issues.

   **MANDATORY SCAN CHECKLIST** — actively check whether the Court ruled on each of the following. If it did, it MUST appear as a separate entry:
   - Quantum or standard of proof (proof beyond reasonable doubt, substantial evidence, clear and convincing evidence, preponderance)
   - Civil liability, indemnity, or damages — amounts, legal basis, adjustments
   - Legal interest rates and the Nacar v. Gallery Frames guidelines
   - Procedural due process — notice, hearing, right to be heard
   - Prescription, laches, or estoppel
   - Jurisdiction — subject matter, appellate, ancillary, or concurrent
   - Standing / locus standi / real-party-in-interest
   - Mootness doctrine or its recognized exceptions
   - Proper remedy or mode of review (Rule 45 vs. Rule 65, appeal vs. certiorari, etc.)
   - Good faith or bad faith of officers or parties and its legal consequences
   - Retroactivity or prospective application of rulings or statutes
   - Definition or first-impression clarification of a legal term or concept
   - Evidentiary rules — admissibility, weight, presumptions, or burden of proof
   - Solidary vs. joint liability; individual vs. collective or vicarious liability
   - Constitutional provisions applied only incidentally
   - Remedial or procedural anomalies settled by the Court motu proprio

   **STRICT RULES:**
   - Extract EVERY collateral ruling that satisfies the checklist above. Do NOT limit yourself — if 7 exist, list all 7.
   - If there are genuinely no secondary rulings, return `[]`. Do NOT invent data.
   - Each object MUST have exactly these two keys:
     - **topic**: A precise, specific label — never generic. Bad: 'Procedural Due Process'. Good: 'Right to Be Heard — Waiver by Failure to Object'. Bad: 'Civil Liability'. Good: 'Solidary Liability of Approving Officers — Gross Negligence Standard'.
     - **ruling**: Write this EXACTLY like a ratio decidendi entry — a minimum of 8-10 sentences of deep, flowing, forensic legal analysis in a single coherent prose paragraph. DO NOT summarize. DO NOT write in telegraphic style. Follow the Court's own chain of reasoning from premise to conclusion: begin with the legal principle or doctrinal anchor, develop it through the specific statutory provisions and landmark precedents the Court cited (name them explicitly — e.g., "Applying the doctrine in *Tan-Andal v. Andal*...", "Under Article 2154 of the Civil Code..."), trace the Court's application of that reasoning to the facts of this case, address any qualifications or exceptions the Court recognized, and close with the precise legal consequence or holding. Use natural academic transitions (e.g., "Consequently," "However," "Moreover," "In this regard," "Thus,"). Every sentence must add substantive legal content — no filler, no restatement, no circular reasoning.

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


SECONDARY_RULINGS_ONLY_PROMPT = """\
You are given a Philippine Supreme Court decision.

YOUR TASK: Scan the ENTIRE decision text with forensic precision and extract EVERY secondary, collateral, or incidental legal ruling that the Court settled beyond the primary issues.

You are acting as a Philippine Bar Exam coach. Active checking of whether the Court ruled on each of the following:
- Quantum or standard of proof (proof beyond reasonable doubt, substantial evidence, clear and convincing evidence, preponderance)
- Civil liability, indemnity, or damages — amounts, legal basis, adjustments
- Legal interest rates and the Nacar v. Gallery Frames guidelines
- Procedural due process — notice, hearing, right to be heard
- Prescription, laches, or estoppel
- Jurisdiction — subject matter, appellate, ancillary, or concurrent
- Standing / locus standi / real-party-in-interest
- Mootness doctrine or its recognized exceptions
- Proper remedy or mode of review (Rule 45 vs. Rule 65, appeal vs. certiorari, etc.)
- Good faith or bad faith of officers or parties and its legal consequences
- Retroactivity or prospective application of rulings or statutes
- Definition or first-impression clarification of a legal term or concept
- Evidentiary rules — admissibility, weight, presumptions, or burden of proof
- Solidary vs. joint liability; individual vs. collective or vicarious liability
- Constitutional provisions applied only incidentally
- Remedial or procedural anomalies settled by the Court motu proprio

STRICT RULES:
- Extract EVERY collateral ruling that satisfies the checklist above. Do NOT limit yourself — if 7 exist, list all 7.
- If there are genuinely no secondary rulings, return []. Do NOT invent data.
- Each object MUST have exactly these two keys:
  - **topic**: A precise, specific label — never generic. Bad: 'Procedural Due Process'. Good: 'Right to Be Heard — Waiver by Failure to Object'. Bad: 'Civil Liability'. Good: 'Solidary Liability of Approving Officers — Gross Negligence Standard'.
  - **ruling**: Write this EXACTLY like a ratio decidendi entry — a minimum of 8-10 sentences of deep, flowing, forensic legal analysis in a single coherent prose paragraph. DO NOT summarize. DO NOT write in telegraphic style. Follow the Court's own chain of reasoning from premise to conclusion: begin with the legal principle or doctrinal anchor, develop it through the specific statutory provisions and landmark precedents the Court cited (name them explicitly — e.g., "Applying the doctrine in *Tan-Andal v. Andal*...", "Under Article 2154 of the Civil Code..."), trace the Court's application of that reasoning to the facts of this case, address any qualifications or exceptions the Court recognized, and close with the precise legal consequence or holding. Use natural academic transitions (e.g., "Consequently," "However," "Moreover," "In this regard," "Thus,"). Every sentence must add substantive legal content — no filler, no restatement, no circular reasoning.

OUTPUT FORMAT:
You MUST return ONLY a valid JSON list of objects with the schema:
[
    {{"topic": "...", "ruling": "..."}}
]

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
        logging.FileHandler("redigest_flagged_decades.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# ── DB helpers ───────────────────────────────────────────────────────────────

def fetch_case(conn, case_id: int) -> dict | None:
    cur = conn.cursor()
    cur.execute(
        "SELECT id, case_number, short_title, full_text_md, ai_model "
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
        "ai_model":     row[4] or "",
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
    # Log history audit entry
    cur.execute(
        """
        INSERT INTO sc_case_digest_history (case_id, ai_model, action, fields_changed)
        VALUES (%s, %s, %s, %s)
        """,
        (
            case_id,
            model,
            'redigest',
            ['main_doctrine', 'digest_issues', 'digest_ratio', 'secondary_rulings']
        )
    )
    conn.commit()
    cur.close()


def save_secondary_rulings_only(conn, case_id: int, secondary_rulings: list | dict, model: str) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE sc_decided_cases
        SET secondary_rulings = %s,
            ai_model = %s,
            updated_at = NOW()
        WHERE id = %s
        """,
        (
            json.dumps(secondary_rulings),
            model,
            case_id,
        ),
    )
    # Log history audit entry
    cur.execute(
        """
        INSERT INTO sc_case_digest_history (case_id, ai_model, action, fields_changed)
        VALUES (%s, %s, %s, %s)
        """,
        (
            case_id,
            model,
            'redigest',
            ['secondary_rulings']
        )
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


def validate_secondary_rulings(raw) -> list:
    """Coerce secondary_rulings to a clean list of {topic, ruling} dicts.

    Handles: nested JSON string, non-list, missing keys, wrong types.
    Returns an empty list rather than raising on bad input.
    """
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return []
    if not isinstance(raw, list):
        return []
    result = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        topic = item.get("topic")
        ruling = item.get("ruling")
        if isinstance(topic, str) and topic.strip() and isinstance(ruling, str) and ruling.strip():
            result.append({"topic": topic.strip(), "ruling": ruling.strip()})
    return result


def generate_digest_data(client: genai.Client, case: dict, model_name: str) -> dict | None:
    full_text = case["full_text_md"] or ""

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
            # Instantly intercept Google gateway-level safety / prohibited content blocks
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                reason_str = str(response.prompt_feedback.block_reason)
                if "PROHIBITED_CONTENT" in reason_str:
                    log.warning("Case ID %s was blocked by Google gateway-level safety: %s. Skipping Gemini retries.", case["id"], reason_str)
                    return "_SAFETY_BLOCKED"

            text = (response.text or "").strip()
            if text:
                cleaned_text = clean_json_text(text)
                try:
                    data = json.loads(cleaned_text)
                    # Verify required fields
                    required_keys = {"main_doctrine", "digest_issues", "digest_ratio", "secondary_rulings"}
                    if all(k in data for k in required_keys):
                        data["secondary_rulings"] = validate_secondary_rulings(data["secondary_rulings"])
                        return data
                    log.warning("Missing keys in JSON for id=%s on attempt %d: %s", case["id"], attempt, data.keys())
                except json.JSONDecodeError as jde:
                    log.warning("JSON decode failed for id=%s on attempt %d: %s\nText: %s", case["id"], attempt, jde, text[:200])
            else:
                log.warning("Empty response on attempt %d for id=%s", attempt, case["id"])
        except Exception as exc:
            exc_str = str(exc).upper()
            if "PROHIBITED_CONTENT" in exc_str or "SAFETY" in exc_str or "BLOCKED" in exc_str:
                log.warning("Case ID %s hit safety block exception: %s. Skipping Gemini retries and falling back.", case["id"], exc)
                return "_SAFETY_BLOCKED"
            log.warning("Attempt %d failed for id=%s: %s", attempt, case["id"], exc)
            if attempt < _RETRY_LIMIT:
                time.sleep(_RETRY_DELAY * attempt)
    return None


def generate_secondary_rulings_only(client: genai.Client, case: dict, model_name: str) -> list | str | None:
    full_text = case["full_text_md"] or ""

    prompt = SECONDARY_RULINGS_ONLY_PROMPT.format(
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
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                reason_str = str(response.prompt_feedback.block_reason)
                if "PROHIBITED_CONTENT" in reason_str:
                    log.warning("Case ID %s was blocked by Google gateway-level safety: %s. Skipping Gemini retries.", case["id"], reason_str)
                    return "_SAFETY_BLOCKED"

            text = (response.text or "").strip()
            if text:
                cleaned_text = clean_json_text(text)
                try:
                    data = json.loads(cleaned_text)
                    return validate_secondary_rulings(data)
                except json.JSONDecodeError as jde:
                    log.warning("JSON decode failed for id=%s on attempt %d: %s\nText: %s", case["id"], attempt, jde, text[:200])
            else:
                log.warning("Empty response on attempt %d for id=%s", attempt, case["id"])
        except Exception as exc:
            exc_str = str(exc).upper()
            if "PROHIBITED_CONTENT" in exc_str or "SAFETY" in exc_str or "BLOCKED" in exc_str:
                log.warning("Case ID %s hit safety block exception: %s. Skipping Gemini retries and falling back.", case["id"], exc)
                return "_SAFETY_BLOCKED"
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

    # Skip if already redigested by this exact model or by Grok fallback
    if case.get("ai_model") in (model_name, "grok-4-1-fast-reasoning", "grok-2"):
        log.info("Case ID %d already redigested by %s. Skipping.", case_id, case.get("ai_model"))
        return True

    log.info("Starting Case ID %d: %s — %s (Size: %d chars)", case["id"], case["case_number"], case["short_title"], len(case["full_text_md"]))

    if limiter:
        limiter.acquire()

    is_legacy_gemini = (case.get("ai_model") == "gemini-3.5-flash")

    if is_legacy_gemini:
        log.info("Case ID %d was digested by legacy gemini-3.5-flash. Redigesting ONLY Secondary Rulings.", case_id)
        secondary_rulings = generate_secondary_rulings_only(client, case, model_name)
        if secondary_rulings == "_SAFETY_BLOCKED":
            log.warning("Case ID %d was blocked due to prohibited content. Triggering Grok fallback immediately.", case_id)
            if dry_run:
                log.info("[DRY RUN] Would invoke Grok fallback for Case ID %d.", case_id)
                return True
            
            grok_script = _SCRIPTS / "generate_sc_digests_grok.py"
            grok_model = os.environ.get("GROK_DIGEST_MODEL") or "grok-4-1-fast-reasoning"
            cmd = [
                sys.executable,
                str(grok_script),
                "--force",
                "--target-ids",
                str(case_id),
                "--model",
                grok_model,
                "--limit",
                "1",
                "--workers",
                "10",
            ]
            log.info("Running Grok fallback subprocess: %s", " ".join(cmd))
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
                if res.returncode == 0:
                    log.info("Grok fallback subprocess completed successfully for Case ID %d", case_id)
                    return True
                else:
                    log.error("Grok fallback subprocess failed for Case ID %d. Return code: %d. Error:\n%s", case_id, res.returncode, res.stderr)
                    return False
            except Exception as e:
                log.error("Failed to run Grok fallback subprocess for Case ID %d: %s", case_id, e)
                return False

        if secondary_rulings is None:
            log.error("Generation failed for Secondary Rulings of Case ID %d", case_id)
            return False

        if dry_run:
            log.info("DRY RUN for Case ID %d. Extracted Secondary Rulings:\n%s", case_id, json.dumps(secondary_rulings, indent=2))
            return True

        with db_lock:
            try:
                save_secondary_rulings_only(conn, case_id, secondary_rulings, model_name)
                log.info("Successfully updated Secondary Rulings for Case ID %d", case_id)
                return True
            except Exception as e:
                log.error("Database save failed for Case ID %d: %s", case_id, e)
                conn.rollback()
                return False

    else:
        data = generate_digest_data(client, case, model_name)
        if data == "_SAFETY_BLOCKED":
            log.warning("Case ID %d was blocked due to prohibited content. Triggering Grok fallback immediately.", case_id)
            if dry_run:
                log.info("[DRY RUN] Would invoke Grok fallback for Case ID %d.", case_id)
                return True
            
            grok_script = _SCRIPTS / "generate_sc_digests_grok.py"
            grok_model = os.environ.get("GROK_DIGEST_MODEL") or "grok-4-1-fast-reasoning"
            cmd = [
                sys.executable,
                str(grok_script),
                "--force",
                "--target-ids",
                str(case_id),
                "--model",
                grok_model,
                "--limit",
                "1",
                "--workers",
                "10",
            ]
            log.info("Running Grok fallback subprocess: %s", " ".join(cmd))
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
                if res.returncode == 0:
                    log.info("Grok fallback subprocess completed successfully for Case ID %d", case_id)
                    return True
                else:
                    log.error("Grok fallback subprocess failed for Case ID %d. Return code: %d. Error:\n%s", case_id, res.returncode, res.stderr)
                    return False
            except Exception as e:
                log.error("Failed to run Grok fallback subprocess for Case ID %d: %s", case_id, e)
                return False

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


# ── Checkpoint ───────────────────────────────────────────────────────────────

_CHECKPOINT_PATH = _SCRIPTS / "redigest_checkpoint.json"


def load_checkpoint(path: Path) -> set[str]:
    if path.is_file():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()


def save_checkpoint(path: Path, completed: set[str]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sorted(completed), f, indent=2)


# ── Progress Reporter ─────────────────────────────────────────────────────────

class ProgressReporter:
    """Background thread that logs batch progress every 5 minutes."""

    INTERVAL = 300  # seconds

    def __init__(self, batch_name: str, total: int) -> None:
        self._batch  = batch_name
        self._total  = total
        self._done   = 0
        self._lock   = threading.Lock()
        self._start  = time.monotonic()
        self._stop   = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="progress")

    def increment(self) -> None:
        with self._lock:
            self._done += 1

    def _report(self) -> None:
        with self._lock:
            done    = self._done
            total   = self._total
            elapsed = time.monotonic() - self._start
        rate    = done / elapsed * 60 if elapsed > 0 else 0
        pct     = done / total * 100 if total else 0
        eta_min = (total - done) / rate if rate > 0 else float("inf")
        log.info(
            "[PROGRESS] %s | %d/%d (%.1f%%) | %.1f cases/min | ETA ~%.0f min",
            self._batch, done, total, pct, rate, eta_min,
        )

    def _loop(self) -> None:
        while not self._stop.wait(self.INTERVAL):
            self._report()

    def start(self) -> "ProgressReporter":
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2)
        self._report()


# ── Batch Builder ─────────────────────────────────────────────────────────────

def build_batches(decadal_split_path: Path, conn) -> list[tuple[str, list[int]]]:
    """Returns ordered batches: 'gaerlan_cases' (first), then 4 En Banc (by decade DESC), then N Division (by year DESC)."""
    from collections import defaultdict

    with open(decadal_split_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Gather all Gaerlan case IDs from DB
    cur = conn.cursor()
    cur.execute("""
        SELECT id FROM sc_decided_cases
        WHERE ponente ILIKE '%Gaerlan%'
    """)
    gaerlan_ids = [row[0] for row in cur.fetchall()]
    cur.close()

    # Gather all IDs from decadal_split.json to filter them
    all_split_ids = set()
    for dec in data:
        all_split_ids.update(data[dec].get("eb_ids", []))
        all_split_ids.update(data[dec].get("div_ids", []))

    # Identify the unmatched Gaerlan case IDs
    unmatched_gaerlan_ids = [gid for gid in gaerlan_ids if gid not in all_split_ids]

    decades = ["2020-2026", "2010-2019", "2000-2009", "1987-1999"]
    batches: list[tuple[str, list[int]]] = []

    # Prepend the Gaerlan Cases batch if there are unmatched cases
    if unmatched_gaerlan_ids:
        batches.append(("gaerlan_cases", unmatched_gaerlan_ids))
        log.info("Gaerlan Cases batch 'gaerlan_cases': %d cases", len(unmatched_gaerlan_ids))

    all_div: list[int] = []

    for dec in decades:
        if dec not in data:
            continue
        eb_ids  = data[dec].get("eb_ids", [])
        div_ids = data[dec].get("div_ids", [])
        if eb_ids:
            batches.append((f"eb_{dec}", eb_ids))
            log.info("En Banc batch 'eb_%s': %d cases", dec, len(eb_ids))
        all_div.extend(div_ids)

    # Fetch case years from DB, then group division IDs per year
    if all_div:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, EXTRACT(YEAR FROM date)::int "
            "FROM sc_decided_cases WHERE id = ANY(%s)",
            (all_div,),
        )
        year_map: dict[int, int] = {row[0]: row[1] or 0 for row in cur.fetchall()}
        cur.close()

        by_year: dict[int, list[int]] = defaultdict(list)
        for cid in all_div:
            by_year[year_map.get(cid, 0)].append(cid)

        for yr in sorted(by_year, reverse=True):
            ids = by_year[yr]
            batches.append((f"div_{yr}", ids))
            log.info("Division batch 'div_%s': %d cases", yr, len(ids))

    total = sum(len(ids) for _, ids in batches)
    log.info("Total batches: %d | Total cases: %d", len(batches), total)
    return batches


class RobustConnection:
    def __init__(self, db_url):
        self.db_url = db_url
        self.conn = psycopg2.connect(db_url)

    def cursor(self):
        try:
            if self.conn.closed:
                log.warning("Database connection is closed. Reconnecting...")
                self.conn = psycopg2.connect(self.db_url)
            else:
                # Try a quick test query to ensure connection is actually alive
                cur = self.conn.cursor()
                cur.execute("SELECT 1")
                cur.fetchone()
                cur.close()
        except Exception as e:
            log.warning("Database connection test failed (%s). Reconnecting...", e)
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = psycopg2.connect(self.db_url)
        return self.conn.cursor()

    def commit(self):
        self.conn.commit()

    def rollback(self):
        try:
            self.conn.rollback()
        except Exception:
            pass

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass

    @property
    def closed(self):
        return self.conn.closed


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Redigest core case fields post-1987. Processes one batch per run; "
                    "resumes from checkpoint on the next run."
    )
    parser.add_argument("--id",               type=int,  help="Run only on a specific case ID (bypasses batch logic)")
    parser.add_argument("--retry-ids",        nargs="+", type=int, help="Retry a specific list of case IDs (bypasses batch/checkpoint logic)")
    parser.add_argument("--limit",            type=int,  help="Cap cases within the current batch")
    parser.add_argument("--threads",          type=int,  default=DEFAULT_THREADS, help="Worker threads per batch")
    parser.add_argument("--rpm",              type=int,  default=200,    help="Vertex AI RPM rate limit")
    parser.add_argument("--dry-run",          action="store_true",       help="Print updates without writing to DB or checkpoint")
    parser.add_argument("--model",            default=MODEL,             help="Vertex AI Gemini model")
    parser.add_argument("--vertex-project",   default=DEFAULT_PROJECT,   help="Vertex AI project")
    parser.add_argument("--vertex-location",  default=DEFAULT_LOCATION,  help="Vertex AI location")
    parser.add_argument("--split-file",       help="Path to decadal_split.json")
    parser.add_argument("--checkpoint-file",  help="Path to checkpoint JSON (default: redigest_checkpoint.json)")
    args = parser.parse_args()

    # ── Resolve split file ────────────────────────────────────────────────────
    split_path = None
    if args.split_file:
        split_path = Path(args.split_file)
    else:
        possible_paths = [
            _SCRIPTS.parent / "scratch" / "decadal_split.json",
            Path("C:/Users/rnlar/.gemini/antigravity/brain/ac8796fd-0d6a-4d86-bb3e-30e75fc2ba03/scratch/decadal_split.json"),
            _SCRIPTS / "decadal_split.json",
        ]
        for p in possible_paths:
            if p.is_file():
                split_path = p
                break

    if not args.id and (not split_path or not split_path.is_file()):
        print(f"Error: decadal_split.json not found. Searched: {[str(p) for p in possible_paths]}", file=sys.stderr)
        sys.exit(1)

    checkpoint_path = Path(args.checkpoint_file) if args.checkpoint_file else _CHECKPOINT_PATH

    print(f"Database : {DB_URL.split('@')[-1] if '@' in DB_URL else DB_URL}")
    print(f"Model    : {args.model}")
    print(f"Project  : {args.vertex_project}")
    print(f"Checkpoint: {checkpoint_path}")

    # ── DB connection ─────────────────────────────────────────────────────────
    try:
        conn = RobustConnection(DB_URL)
    except Exception as e:
        print(f"Failed to connect to database: {e}", file=sys.stderr)
        sys.exit(1)

    db_lock = threading.Lock()
    limiter  = RateLimiter(args.rpm) if args.rpm > 0 else None

    # ── Vertex AI client ──────────────────────────────────────────────────────
    try:
        client = _build_client(args.vertex_project, args.vertex_location)
    except Exception as e:
        print(f"Failed to build Vertex AI client: {e}", file=sys.stderr)
        sys.exit(1)

    # ── Single-case mode ──────────────────────────────────────────────────────
    if args.id:
        print(f"Single-case mode: ID {args.id}")
        ok = process_case(client, conn, db_lock, args.id, args.dry_run, args.model, limiter)
        conn.close()
        sys.exit(0 if ok else 1)

    # ── Retry-IDs mode ────────────────────────────────────────────────────────
    if args.retry_ids:
        ids = args.retry_ids
        log.info("=" * 60)
        log.info("RETRY MODE: %d case IDs | %d threads", len(ids), args.threads)
        log.info("=" * 60)
        reporter = ProgressReporter("retry", len(ids)).start()
        success_count = failure_count = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads) as executor:
            futures = {
                executor.submit(
                    process_case, client, conn, db_lock,
                    cid, args.dry_run, args.model, limiter
                ): cid
                for cid in ids
            }
            for fut in concurrent.futures.as_completed(futures):
                cid = futures[fut]
                try:
                    if fut.result():
                        success_count += 1
                    else:
                        failure_count += 1
                except Exception as e:
                    log.exception("Unexpected error for Case ID %d: %s", cid, e)
                    failure_count += 1
                reporter.increment()
        reporter.stop()
        log.info("RETRY DONE | OK %d | ERR %d", success_count, failure_count)
        conn.close()
        sys.exit(0 if failure_count == 0 else 1)

    # ── Batch mode ────────────────────────────────────────────────────────────
    completed_batches = load_checkpoint(checkpoint_path)
    print(f"Checkpoint: {len(completed_batches)} batch(es) already done")

    batches = build_batches(split_path, conn)

    for batch_name, batch_ids in batches:
        if batch_name in completed_batches:
            log.info("SKIP (done): %s  (%d cases)", batch_name, len(batch_ids))
            continue

        if args.limit:
            batch_ids = batch_ids[: args.limit]
            log.info("Batch capped to %d cases by --limit", args.limit)

        log.info("=" * 60)
        log.info("BATCH START: %s  |  %d cases  |  %d threads", batch_name, len(batch_ids), args.threads)
        log.info("=" * 60)

        reporter     = ProgressReporter(batch_name, len(batch_ids)).start()
        success_count = 0
        failure_count = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads) as executor:
            futures = {
                executor.submit(
                    process_case, client, conn, db_lock,
                    cid, args.dry_run, args.model, limiter
                ): cid
                for cid in batch_ids
            }
            for fut in concurrent.futures.as_completed(futures):
                cid = futures[fut]
                try:
                    if fut.result():
                        success_count += 1
                    else:
                        failure_count += 1
                except Exception as e:
                    log.exception("Unexpected error for Case ID %d: %s", cid, e)
                    failure_count += 1
                reporter.increment()

        reporter.stop()

        log.info("=" * 60)
        log.info("BATCH DONE : %s  |  OK %d  |  ERR %d", batch_name, success_count, failure_count)
        log.info("=" * 60)

        if not args.dry_run and not args.limit:
            completed_batches.add(batch_name)
            save_checkpoint(checkpoint_path, completed_batches)
            log.info("Checkpoint saved -> %s", checkpoint_path)
            log.info("Re-run to continue with the next batch.")
        else:
            log.info("Dry run or limited run — checkpoint not updated.")

        break  # one batch per run

    else:
        log.info("All %d batches completed.", len(batches))

    conn.close()


if __name__ == "__main__":
    main()
