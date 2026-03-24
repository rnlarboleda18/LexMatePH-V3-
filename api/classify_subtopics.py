"""
Lexify Sub-Topic Batch Classifier
==================================
One-time script to classify each question in the DB into one of the
13 Philippine Bar 2026 sub-topics using Gemini AI.

Usage (from /api directory with venv activated):
    python classify_subtopics.py

Requirements:
    - GEMINI_API_KEY or GOOGLE_API_KEY env var set (or in local.settings.json)
    - psycopg2, requests packages available
    - The questions table must already have the sub_topic column (run migration first)

Estimated runtime: ~90 minutes for 5,000 questions (batched in groups of 10)
"""

import os
import json
import time
import logging
import requests
import psycopg2
from psycopg2.extras import RealDictCursor

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Load from local.settings.json if env not set
def load_settings():
    try:
        with open("local.settings.json") as f:
            data = json.load(f)
            vals = data.get("Values", {})
            for k, v in vals.items():
                if k not in os.environ:
                    os.environ[k] = v
    except Exception:
        pass

load_settings()

DB_CONN_STR = os.environ.get("DB_CONNECTION_STRING") or os.environ.get("DATABASE_URL", "")
if ":6432/" in DB_CONN_STR:
    DB_CONN_STR = DB_CONN_STR.replace(":6432/", ":5432/")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
BATCH_SIZE = 10          # Questions per Gemini call (balance cost vs speed)
SLEEP_BETWEEN_BATCHES = 1.0   # Seconds between API calls (avoid rate limiting)

# ---------------------------------------------------------------------------
# Valid Sub-Topics (the 13 accepted values)
# ---------------------------------------------------------------------------

VALID_SUBTOPICS = {
    "Political Law",
    "Public International Law",
    "Commercial Law",
    "Taxation",
    "Civil Law",
    "Land Titles and Deeds",
    "Labor Law",
    "Social Legislation",
    "Criminal Law",
    "Special Penal Laws",
    "Remedial Law",
    "Legal and Judicial Ethics",
    "Practical Exercises",
}

# DB subject → most likely sub-topic pool (used for validation / fallback)
SUBJECT_SUBTOPIC_MAP = {
    "Political Law":     ["Political Law", "Public International Law"],
    "Commercial Law":    ["Commercial Law", "Taxation"],
    "Taxation Law":      ["Taxation", "Commercial Law"],
    "Civil Law":         ["Civil Law", "Land Titles and Deeds"],
    "Labor Law":         ["Labor Law", "Social Legislation"],
    "Criminal Law":      ["Criminal Law", "Special Penal Laws"],
    "Remedial Law":      ["Remedial Law", "Legal and Judicial Ethics", "Practical Exercises"],
    "Legal Ethics":      ["Legal and Judicial Ethics", "Practical Exercises", "Remedial Law"],
}

# ---------------------------------------------------------------------------
# Gemini Classifier
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a Philippine Bar Exam subject classifier. 
Classify each question into exactly ONE sub-topic from this list:

1. Political Law
2. Public International Law
3. Commercial Law
4. Taxation
5. Civil Law
6. Land Titles and Deeds
7. Labor Law
8. Social Legislation
9. Criminal Law
10. Special Penal Laws
11. Remedial Law
12. Legal and Judicial Ethics
13. Practical Exercises

CLASSIFICATION RULES:
- "Political Law": constitutional law, government structure, bill of rights, admin law, election law
- "Public International Law": treaties, Vienna Convention, ICJ, state responsibility, UNCLOS, diplomatic law
- "Commercial Law": corporations, partnerships, securities, negotiable instruments, insurance, banking, e-commerce
- "Taxation": income tax, VAT, excise tax, BIR, NIRC, TRAIN law, local taxation, customs
- "Civil Law": persons, family, obligations, contracts, sales, property, prescription, torts, succession
- "Land Titles and Deeds": Torrens system, LRA, Register of Deeds, original registration, adverse claim, annotation
- "Labor Law": Labor Code, employment standards, labor relations, unions, NLRC, dismissal
- "Social Legislation": SSS, GSIS, PhilHealth, Pag-IBIG, social security, workers compensation, DOLE agencies
- "Criminal Law": Revised Penal Code, felonies, penalties, principals/accessories, circumstances
- "Special Penal Laws": RA laws — drug offenses, cybercrime, VAWC, anti-trafficking, graft, plunder, anti-graft
- "Remedial Law": Rules of Court, civil procedure, criminal procedure, evidence, appellate procedure
- "Legal and Judicial Ethics": CPRA, lawyer duties, bar admission, sanctions, judicial conduct
- "Practical Exercises": Legal drafting, verification, motions, pleadings, legal forms

Respond ONLY with a JSON array of sub-topic strings, one per question, in the same order.
Example for 3 questions: ["Political Law", "Civil Law", "Remedial Law"]"""


def classify_batch(questions: list[dict]) -> list[str | None]:
    """Send a batch of questions to Gemini and return sub-topic list."""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not set")

    # Build numbered question list
    user_content_lines = []
    for i, q in enumerate(questions, 1):
        text = q.get("text", "").strip()[:400]  # Truncate to keep tokens low
        user_content_lines.append(f"Q{i} [{q.get('subject', '')}]: {text}")
    user_content = "\n\n".join(user_content_lines)

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite-preview:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": user_content}]}],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.0,
            "maxOutputTokens": 256,
        }
    }

    try:
        resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        text_out = data["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(text_out)

        if not isinstance(parsed, list) or len(parsed) != len(questions):
            log.warning(f"Unexpected response length: {parsed}")
            return [None] * len(questions)

        # Validate each returned value
        validated = []
        for i, (tag, q) in enumerate(zip(parsed, questions)):
            if tag in VALID_SUBTOPICS:
                validated.append(tag)
            else:
                # Fallback: use first expected sub-topic for this DB subject
                db_subject = q.get("subject", "")
                fallback = SUBJECT_SUBTOPIC_MAP.get(db_subject, [None])[0]
                log.warning(f"Q{i+1} invalid tag '{tag}' → fallback '{fallback}'")
                validated.append(fallback)
        return validated

    except Exception as e:
        log.error(f"Gemini batch error: {e}")
        return [None] * len(questions)


# ---------------------------------------------------------------------------
# Main: Fetch untagged questions → classify → update DB
# ---------------------------------------------------------------------------

def main():
    log.info("=== Lexify Sub-Topic Batch Classifier ===")

    if not DB_CONN_STR:
        log.error("DATABASE_URL not set. Check local.settings.json.")
        return

    conn = psycopg2.connect(DB_CONN_STR)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Count untagged
    cur.execute("SELECT COUNT(*) FROM questions WHERE sub_topic IS NULL")
    total_untagged = cur.fetchone()["count"]
    log.info(f"Found {total_untagged} untagged questions")

    if total_untagged == 0:
        log.info("All questions are already tagged. Done.")
        cur.close(); conn.close()
        return

    # Fetch in batches
    offset = 0
    total_tagged = 0
    total_failed = 0

    while True:
        cur.execute(
            """SELECT id, subject, text FROM questions 
               WHERE sub_topic IS NULL 
               ORDER BY id ASC 
               LIMIT %s OFFSET %s""",
            (BATCH_SIZE, offset)
        )
        batch = cur.fetchall()
        if not batch:
            break

        log.info(f"Processing batch offset={offset} size={len(batch)} ...")
        subtopics = classify_batch(batch)

        # Update each question
        upd_cur = conn.cursor()
        for q, topic in zip(batch, subtopics):
            if topic:
                upd_cur.execute(
                    "UPDATE questions SET sub_topic = %s WHERE id = %s",
                    (topic, q["id"])
                )
                total_tagged += 1
            else:
                total_failed += 1
        conn.commit()
        upd_cur.close()

        progress = min(offset + BATCH_SIZE, total_untagged)
        log.info(f"Progress: {progress}/{total_untagged} ({(progress/total_untagged)*100:.1f}%)")

        offset += BATCH_SIZE
        time.sleep(SLEEP_BETWEEN_BATCHES)

    cur.close()
    conn.close()

    log.info("=== DONE ===")
    log.info(f"Successfully tagged : {total_tagged}")
    log.info(f"Failed / unresolved : {total_failed}")
    log.info("Run the SQL verification query to confirm the distribution.")


if __name__ == "__main__":
    main()
