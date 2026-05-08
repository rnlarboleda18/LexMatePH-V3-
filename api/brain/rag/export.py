"""
Export legal corpus from PostgreSQL to GCS for Vertex AI RAG Engine ingestion.

Run directly:
    python -m api.brain.rag.export --source cases --batch-size 500
    python -m api.brain.rag.export --source statutes
    python -m api.brain.rag.export --source all

Each document is written as structured plain text (.txt) — format RAG Engine
chunks well. One file per case/provision. Skips already-uploaded files.
"""

import argparse
import hashlib
import json
import logging
import os
import sys
from datetime import date
from io import BytesIO

import psycopg2
import psycopg2.extras
from google.cloud import storage
from google.api_core.exceptions import GoogleAPICallError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

if config.GCP_CREDENTIALS_FILE and os.path.exists(config.GCP_CREDENTIALS_FILE):
    os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", config.GCP_CREDENTIALS_FILE)


# ── Document formatters ────────────────────────────────────────────────────────

def format_case(row: dict) -> str:
    """Format a case row into structured plain text for RAG ingestion."""
    lines = [
        "=== CASE METADATA ===",
        f"Title: {row.get('full_title') or row.get('short_title', 'Unknown')}",
        f"Short Title: {row.get('short_title', '')}",
        f"GR Number: {row.get('case_number', '')}",
        f"Date: {row.get('date', '')}",
        f"Ponente: {row.get('ponente', '')}",
        f"Division: {row.get('division', '')}",
        f"Document Type: {row.get('document_type', '')}",
        f"Subject: {row.get('subject', '')}",
        f"Doctrinal: {'Yes' if row.get('is_doctrinal') else 'No'}",
    ]

    # Keywords and legal concepts for better retrieval
    if row.get("keywords"):
        kw = row["keywords"]
        if isinstance(kw, str):
            kw = json.loads(kw)
        lines.append(f"Keywords: {', '.join(kw) if isinstance(kw, list) else str(kw)}")

    if row.get("legal_concepts"):
        lc = row["legal_concepts"]
        if isinstance(lc, str):
            lc = json.loads(lc)
        if isinstance(lc, list):
            lines.append(f"Legal Concepts: {', '.join(str(c) for c in lc[:10])}")

    if row.get("statutes_involved"):
        si = row["statutes_involved"]
        if isinstance(si, str):
            si = json.loads(si)
        if isinstance(si, list):
            lines.append(f"Statutes Involved: {', '.join(str(s) for s in si)}")

    # Main doctrine — highest retrieval priority
    if row.get("main_doctrine"):
        lines += ["", "=== MAIN DOCTRINE ===", row["main_doctrine"]]

    # Digest sections — structured, concise, high quality
    if row.get("digest_facts"):
        lines += ["", "=== FACTS ===", row["digest_facts"]]

    if row.get("digest_issues"):
        lines += ["", "=== ISSUES ===", row["digest_issues"]]

    if row.get("digest_ruling"):
        lines += ["", "=== RULING ===", row["digest_ruling"]]

    if row.get("digest_ratio"):
        lines += ["", "=== RATIO DECIDENDI ===", row["digest_ratio"]]

    if row.get("digest_significance"):
        lines += ["", "=== SIGNIFICANCE ===", row["digest_significance"]]

    # Full text — complete source of truth
    if row.get("full_text_md"):
        # Truncate extremely long documents to 800k chars (~200k tokens)
        # Gemini 2.5 Pro can handle 1M tokens but RAG Engine has per-doc limits
        full_text = row["full_text_md"]
        if len(full_text) > 800_000:
            full_text = full_text[:800_000] + "\n\n[Full text truncated — see SC e-Library for complete decision]"
        lines += ["", "=== FULL TEXT ===", full_text]

    return "\n".join(lines)


def format_codal_provision(row: dict, code_name: str) -> str:
    """Format a statutory provision into structured plain text."""
    lines = [
        "=== PROVISION METADATA ===",
        f"Code: {code_name}",
        f"Article: {row.get('article_num', '')} {row.get('article_suffix', '')}".strip(),
        f"Title: {row.get('article_title', '')}",
        f"Section: {row.get('section_label', '') or row.get('chapter_label', '')}",
        f"Book/Part: {row.get('book', '') or row.get('title_label', '')}",
        "",
        "=== PROVISION TEXT ===",
        row.get("content_md", ""),
    ]

    if row.get("elements"):
        el = row["elements"]
        if isinstance(el, str):
            el = json.loads(el)
        if isinstance(el, list) and el:
            lines += ["", "=== ELEMENTS / REQUISITES ==="]
            lines += [f"- {e}" for e in el]

    return "\n".join(lines)


def format_flashcard(row: dict) -> str:
    """Format a legal concept/flashcard into plain text."""
    lines = [
        "=== LEGAL CONCEPT ===",
        f"Term: {row.get('term', '')}",
        f"Key: {row.get('term_key', '')}",
        "",
        "=== DEFINITION ===",
        row.get("definition", ""),
    ]

    if row.get("sources"):
        src = row["sources"]
        if isinstance(src, str):
            src = json.loads(src)
        if isinstance(src, list):
            lines += ["", "=== SOURCES ==="]
            lines += [f"- {s}" for s in src[:10]]

    return "\n".join(lines)


# ── GCS helpers ───────────────────────────────────────────────────────────────

def get_gcs_client() -> storage.Client:
    return storage.Client(project=config.GCP_PROJECT)


def list_existing_blobs(bucket: storage.Bucket, prefix: str) -> set:
    """List all existing blob names under a prefix in one API call."""
    log.info(f"Scanning existing files under gs://{bucket.name}/{prefix} ...")
    existing = {b.name for b in bucket.list_blobs(prefix=prefix)}
    log.info(f"Found {len(existing):,} existing files under {prefix}")
    return existing


def upload_text(bucket: storage.Bucket, blob_name: str, content: str) -> None:
    blob = bucket.blob(blob_name)
    blob.upload_from_string(content.encode("utf-8"), content_type="text/plain; charset=utf-8")


# ── Export functions ───────────────────────────────────────────────────────────

def export_cases(
    cur: psycopg2.extensions.cursor,
    bucket: storage.Bucket,
    batch_size: int = 500,
    doctrinal_only: bool = False,
    resume: bool = True,
) -> dict:
    """Export sc_decided_cases → GCS cases/full-text/"""
    prefix = config.GCS_CASES_PREFIX

    where = "WHERE full_text_md IS NOT NULL AND full_text_md != ''"
    if doctrinal_only:
        where += " AND is_doctrinal = true"

    cur.execute(f"SELECT COUNT(*) FROM sc_decided_cases {where}")
    total = cur.fetchone()[0]
    log.info(f"Exporting {total:,} cases (doctrinal_only={doctrinal_only})")

    # Build existing-files set in ONE list call — avoids 50k individual exists() calls
    existing = list_existing_blobs(bucket, prefix) if resume else set()

    cur2 = cur.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur2.execute(f"""
        SELECT id, case_number, short_title, full_title, date, division,
               document_type, ponente, is_doctrinal, subject, main_doctrine,
               digest_facts, digest_issues, digest_ruling, digest_ratio,
               digest_significance, full_text_md, keywords, legal_concepts,
               statutes_involved
        FROM sc_decided_cases
        {where}
        ORDER BY id
    """)

    stats = {"exported": 0, "skipped": 0, "errors": 0}

    while True:
        rows = cur2.fetchmany(batch_size)
        if not rows:
            break

        for row in rows:
            # Sanitise case number for filename
            cn = (row["case_number"] or f"case-{row['id']}").replace("/", "-").replace(" ", "_")
            blob_name = f"{prefix}/{cn}_{row['id']}.txt"

            if blob_name in existing:
                stats["skipped"] += 1
                continue

            try:
                content = format_case(dict(row))
                upload_text(bucket, blob_name, content)
                stats["exported"] += 1
            except Exception as e:
                log.error(f"Failed case id={row['id']}: {e}")
                stats["errors"] += 1

        done = stats["exported"] + stats["skipped"] + stats["errors"]
        log.info(f"Cases progress: {done:,}/{total:,} — "
                 f"exported={stats['exported']:,} skipped={stats['skipped']:,} errors={stats['errors']:,}")

    return stats


def export_codal(
    cur: psycopg2.extensions.cursor,
    bucket: storage.Bucket,
    resume: bool = True,
) -> dict:
    """Export all codal tables → GCS statutes/provisions/"""
    prefix = config.GCS_PROVISIONS_PREFIX
    stats = {"exported": 0, "skipped": 0, "errors": 0}

    codal_tables = {
        "fc_codal":    "Family Code of the Philippines",
        "rpc_codal":   "Revised Penal Code",
        "civ_codal":   "Civil Code of the Philippines",
        "rcc_codal":   "Revised Corporation Code",
        "labor_codal": "Labor Code of the Philippines",
        "consti_codal":"1987 Philippine Constitution",
        "roc_codal":   "Rules of Court",
    }

    existing = list_existing_blobs(bucket, prefix) if resume else set()

    for table, code_name in codal_tables.items():
        try:
            cur2 = cur.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur2.execute(f"SELECT * FROM {table} ORDER BY list_order, id LIMIT 10000")
        except Exception:
            cur.connection.rollback()
            try:
                cur2 = cur.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur2.execute(f"SELECT * FROM {table} ORDER BY id LIMIT 10000")
            except Exception as e:
                cur.connection.rollback()
                log.warning(f"Skipping {table}: {e}")
                continue

        rows = cur2.fetchall()
        log.info(f"Exporting {table} ({len(rows)} provisions) as '{code_name}'")

        for row in rows:
            row = dict(row)
            art = str(row.get("article_num", row.get("id", "unknown")))
            blob_name = f"{prefix}/{table}/{art.replace('/', '-')}.txt"

            if blob_name in existing:
                stats["skipped"] += 1
                continue

            try:
                content = format_codal_provision(row, code_name)
                upload_text(bucket, blob_name, content)
                stats["exported"] += 1
            except Exception as e:
                log.error(f"Failed {table} art={art}: {e}")
                stats["errors"] += 1

    return stats


def export_flashcards(
    cur: psycopg2.extensions.cursor,
    bucket: storage.Bucket,
    resume: bool = True,
) -> dict:
    """Export flashcard_concepts → GCS bar-exam/"""
    prefix = config.GCS_BAR_PREFIX
    stats = {"exported": 0, "skipped": 0, "errors": 0}

    existing = list_existing_blobs(bucket, prefix) if resume else set()

    cur2 = cur.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur2.execute("SELECT * FROM flashcard_concepts ORDER BY id")
    rows = cur2.fetchall()
    log.info(f"Exporting {len(rows):,} flashcard concepts")

    for row in rows:
        row = dict(row)
        key = (row.get("term_key") or str(row["id"])).replace("/", "-")
        blob_name = f"{prefix}/{key}.txt"

        if blob_name in existing:
            stats["skipped"] += 1
            continue

        try:
            content = format_flashcard(row)
            upload_text(bucket, blob_name, content)
            stats["exported"] += 1
        except Exception as e:
            log.error(f"Failed flashcard id={row['id']}: {e}")
            stats["errors"] += 1

    return stats


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Export LexMatePH corpus to GCS for RAG ingestion")
    parser.add_argument("--source", choices=["cases", "statutes", "flashcards", "all"], default="all")
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--doctrinal-only", action="store_true",
                        help="Export only doctrinal cases (50k instead of 65k)")
    parser.add_argument("--no-resume", action="store_true",
                        help="Re-upload even if file already exists in GCS")
    args = parser.parse_args()

    resume = not args.no_resume
    conn_str = config.LOCAL_DB_CONNECTION_STRING or config.DB_CONNECTION_STRING
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor()

    gcs = get_gcs_client()
    bucket = gcs.bucket(config.GCS_CORPUS_BUCKET)

    log.info(f"Starting export: source={args.source} bucket=gs://{config.GCS_CORPUS_BUCKET}")

    total_stats = {}

    if args.source in ("cases", "all"):
        stats = export_cases(cur, bucket, args.batch_size, args.doctrinal_only, resume)
        total_stats["cases"] = stats
        log.info(f"Cases done: {stats}")

    if args.source in ("statutes", "all"):
        stats = export_codal(cur, bucket, resume)
        total_stats["statutes"] = stats
        log.info(f"Statutes done: {stats}")

    if args.source in ("flashcards", "all"):
        stats = export_flashcards(cur, bucket, resume)
        total_stats["flashcards"] = stats
        log.info(f"Flashcards done: {stats}")

    conn.close()
    log.info(f"Export complete: {json.dumps(total_stats, indent=2)}")


if __name__ == "__main__":
    main()
