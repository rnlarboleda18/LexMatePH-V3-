"""
publish_all_subjects.py — publish all generated draft topics for all 6 subjects.

Run after generation is complete:
    python tools/publish_all_subjects.py

Only publishes topics with real content (not error placeholders or dry-run stubs).
"""
import sys
import os
from pathlib import Path

API_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(API_DIR))

import json
import psycopg2
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def load_settings():
    try:
        with open(API_DIR / "local.settings.json") as f:
            for k, v in json.load(f).get("Values", {}).items():
                if k not in os.environ:
                    os.environ[k] = v
    except Exception:
        pass


def get_conn():
    cs = os.environ.get("DB_CONNECTION_STRING", "")
    if not cs:
        raise RuntimeError("DB_CONNECTION_STRING not set")
    return psycopg2.connect(cs)


def main():
    load_settings()
    conn = get_conn()
    cur = conn.cursor()

    # Count before
    cur.execute("""
        SELECT subject_id, status, COUNT(*) FROM bar_reviewer_topics
        GROUP BY subject_id, status ORDER BY subject_id, status
    """)
    log.info("Current state:")
    for r in cur.fetchall():
        log.info("  %s / %s: %d topics", r[0], r[1], r[2])

    # Publish all non-error, non-dry-run draft topics
    cur.execute("""
        UPDATE bar_reviewer_topics
        SET status = 'published', reviewed_at = NOW()
        WHERE status = 'draft'
          AND doctrine_md NOT LIKE '[Generation error%'
          AND doctrine_md NOT LIKE '[dry-run%'
          AND doctrine_md IS NOT NULL
        RETURNING subject_id, roman_num, sub_letter
    """)
    published = cur.fetchall()
    conn.commit()

    by_subject = {}
    for row in published:
        by_subject.setdefault(row[0], []).append(f"{row[1]}.{row[2] or ''}")

    log.info("\nPublished %d topics:", len(published))
    for subj, topics in sorted(by_subject.items()):
        log.info("  %s: %d topics", subj, len(topics))

    # Report remaining errors/stubs
    cur.execute("""
        SELECT subject_id, roman_num, sub_letter,
               LEFT(doctrine_md, 80) as preview
        FROM bar_reviewer_topics
        WHERE status = 'draft'
        ORDER BY subject_id, sort_order
    """)
    remaining = cur.fetchall()
    if remaining:
        log.warning("\n%d topics still in draft (errors/stubs):", len(remaining))
        for r in remaining:
            log.warning("  %s %s.%s: %s", r[0], r[1], r[2] or '', r[3])
    else:
        log.info("\nAll topics published!")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
