"""
Lexify Sub-Topic Parallel Classifier
====================================
Uses 20 parallel threads with concurrent.futures to process
the 3,085 questions through Gemini 3.1 Flash Lite Preview quickly.
"""

import os
import json
import time
import logging
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

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
if ":5432/" in DB_CONN_STR:
    DB_CONN_STR = DB_CONN_STR.replace(":5432/", ":5432/")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
MAX_WORKERS = 5
BATCH_SIZE = 10  # 10 questions per API request

# ---------------------------------------------------------------------------
# Options & Prompt
# ---------------------------------------------------------------------------

VALID_SUBTOPICS = {
    "Political Law", "Public International Law", "Commercial Law", "Taxation",
    "Civil Law", "Land Titles and Deeds", "Labor Law", "Social Legislation",
    "Criminal Law", "Special Penal Laws", "Remedial Law", "Legal and Judicial Ethics", "Practical Exercises",
}

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

RULES: Respond ONLY with a JSON array of strings in order."""

# ---------------------------------------------------------------------------
# Worker Thread task
# ---------------------------------------------------------------------------

def process_batch(ids_chunk):
    """Worker task: Opens own DB connection, fetches IDs, calls Gemini, saves sub-topic."""
    if not ids_chunk:
        return 0, 0

    try:
        conn = psycopg2.connect(DB_CONN_STR)
        conn.autocommit = True
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # 1. Fetch text for this batch
        cur.execute(
            f"SELECT id, subject, text FROM questions WHERE id IN ({','.join(map(str, ids_chunk))})"
        )
        questions = cur.fetchall()

        if not questions:
            cur.close(); conn.close()
            return 0, 0

        # 2. Call Gemini
        user_content_lines = []
        for i, q in enumerate(questions, 1):
            text = q.get("text", "").strip()[:400]
            user_content_lines.append(f"Q{i} [{q.get('subject', '')}]: {text}")
        user_content = "\n\n".join(user_content_lines)

        # GEMINI 3.1 FLASH LITE PREVIEW
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite-preview:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"parts": [{"text": user_content}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.0,
                "maxOutputTokens": 256,
            }
        }

        resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
        if resp.status_code == 429:
            # Back off slightly if rate limited
            log.warning("Rate limit (429) hit. Backing off 2s...")
            time.sleep(2)
            cur.close(); conn.close()
            return 0, len(questions) # Treat items as failed to retry 

        resp.raise_for_status()
        data = resp.json()
        text_out = data["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(text_out)

        # 3. Save updates
        success_count = 0
        upd_cur = conn.cursor()
        for i, (tag, q) in enumerate(zip(parsed, questions)):
            topic = tag if tag in VALID_SUBTOPICS else SUBJECT_SUBTOPIC_MAP.get(q["subject"], [None])[0]
            if topic:
                upd_cur.execute(
                    "UPDATE questions SET sub_topic = %s WHERE id = %s",
                    (topic, q["id"])
                )
                success_count += 1
        upd_cur.close()
        cur.close()
        conn.close()

        return success_count, len(questions) - success_count

    except Exception as e:
        # log.error(f"Worker Exception: {e}")
        return 0, len(ids_chunk)


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def main():
    log.info("=== Lexify Parallel Classifier Running (20 Workers) ===")

    if not DB_CONN_STR:
        log.error("DATABASE_URL not set")
        return

    # First fetch ALL untagged IDs
    conn = psycopg2.connect(DB_CONN_STR)
    cur = conn.cursor()
    cur.execute("SELECT id FROM questions WHERE sub_topic IS NULL ORDER BY id ASC")
    ids = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()

    total_untagged = len(ids)
    log.info(f"Targeting {total_untagged} untagged questions with {MAX_WORKERS} workers")

    if total_untagged == 0:
        log.info("Already completed.")
        return

    # Chunk IDs into batches of 10
    chunks = [ids[i:i + BATCH_SIZE] for i in range(0, total_untagged, BATCH_SIZE)]

    total_success = 0
    total_failed = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_chunk = {executor.submit(process_batch, chunk): chunk for chunk in chunks}

        completed = 0
        for future in as_completed(future_to_chunk):
            success, failed = future.result()
            total_success += success
            total_failed += failed
            completed += 1

            if completed % 10 == 0 or completed == len(chunks):
                progress = (completed / len(chunks)) * 100
                log.info(f"Progress: {completed}/{len(chunks)} chunks ({progress:.1f}%) | Classified: {total_success} | Errors/Skipped: {total_failed}")

    log.info(f"=== DONE === Total Success: {total_success} | Total Failed: {total_failed}")

if __name__ == "__main__":
    main()
