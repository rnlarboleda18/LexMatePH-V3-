"""
Step 2 — Create sc_issuances_codal table and register statutes.

Reads DB_CONNECTION_STRING from env or local.settings.json.
Idempotent: safe to re-run.
"""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

import psycopg2

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_db_url() -> str:
    s = (os.environ.get("DB_CONNECTION_STRING") or "").strip()
    if s:
        return s
    cfg = _REPO_ROOT / "local.settings.json"
    try:
        vals = json.loads(cfg.read_text(encoding="utf-8")).get("Values", {})
        return (vals.get("DB_CONNECTION_STRING") or "").strip()
    except OSError:
        return ""


STATUTE_REGISTRATIONS = [
    ("AM-07-9-12-SC",  "Rule on the Writ of Amparo (A.M. No. 07-9-12-SC)",                        "SC Issuance"),
    ("AM-08-1-16-SC",  "Rule on the Writ of Habeas Data (A.M. No. 08-1-16-SC)",                   "SC Issuance"),
    ("AM-09-6-8-SC",   "Rules of Procedure for Environmental Cases (A.M. No. 09-6-8-SC)",         "SC Issuance"),
    ("AM-01-7-01-SC",  "Rules on Electronic Evidence (A.M. No. 01-7-01-SC)",                      "SC Issuance"),
    ("CPRA",           "Code of Professional Responsibility and Accountability",                   "SC Issuance"),
    ("AM-02-8-13-SC",  "2004 Rules on Notarial Practice (A.M. No. 02-8-13-SC)",                   "SC Issuance"),
    ("NCJC",           "New Code of Judicial Conduct for the Philippine Judiciary",                "SC Issuance"),
    ("RA-11642",       "Republic Act No. 11642 — Domestic Administrative Adoption and Alternative Child Care Act", "Special Law"),
]


def main() -> None:
    db_url = _load_db_url()
    if not db_url:
        raise RuntimeError("DB_CONNECTION_STRING not found in env or local.settings.json")

    conn = psycopg2.connect(db_url)
    cur  = conn.cursor()

    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'sc_issuances_codal'
        )
    """)
    if cur.fetchone()[0]:
        print("Table sc_issuances_codal already exists — skipping CREATE.")
        # Add part_num/part_label columns if they don't exist yet
        cur.execute("""
            ALTER TABLE sc_issuances_codal
                ADD COLUMN IF NOT EXISTS part_num   VARCHAR(50),
                ADD COLUMN IF NOT EXISTS part_label TEXT
        """)
        print("Ensured part_num / part_label columns exist.")
    else:
        print("Creating sc_issuances_codal ...")
        cur.execute("""
            CREATE TABLE sc_issuances_codal (
                id             UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
                statute_id     VARCHAR(100) NOT NULL,
                statute_label  TEXT,
                group_type     VARCHAR(50),    -- 'Canon', 'Part', 'Chapter', 'Rule', etc.
                group_num      VARCHAR(50),    -- 'I', 'II', '1', '2', etc.
                group_label    TEXT,
                part_num       VARCHAR(50),    -- parent PART/CHAPTER num when group is a RULE
                part_label     TEXT,           -- parent PART/CHAPTER label
                section_num    VARCHAR(50),
                section_title  TEXT,
                content_md     TEXT,
                sort_order     INT          NOT NULL DEFAULT 0,
                created_at     TIMESTAMPTZ  DEFAULT NOW(),
                updated_at     TIMESTAMPTZ  DEFAULT NOW()
            );

            CREATE INDEX sc_issuances_statute_idx
                ON sc_issuances_codal (statute_id);

            CREATE INDEX sc_issuances_sec_idx
                ON sc_issuances_codal (statute_id, section_num);
        """)
        print("Table created.")

    print("\nRegistering statutes ...")
    for alias, full_name, category in STATUTE_REGISTRATIONS:
        cur.execute("SELECT id FROM statutes WHERE alias = %s", (alias,))
        if cur.fetchone():
            print(f"  [skip]   {alias}")
        else:
            cur.execute(
                "INSERT INTO statutes (id, alias, full_name, category) VALUES (%s, %s, %s, %s)",
                (str(uuid.uuid4()), alias, full_name, category),
            )
            print(f"  [insert] {alias}")

    conn.commit()
    cur.close()
    conn.close()
    print("\nSchema setup complete.")


if __name__ == "__main__":
    main()
