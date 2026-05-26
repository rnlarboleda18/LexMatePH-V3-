"""
Migration: Create bar_reviewer_topics and bar_topic_provision_map tables.
Run from the api/ directory: python tools/create_bar_reviewer_tables.py
"""
import os
import json
import psycopg2


def load_settings():
    try:
        with open("local.settings.json") as f:
            data = json.load(f)
            vals = data.get("Values", {})
            db = (vals.get("DB_CONNECTION_STRING") or "").strip()
            for k, v in vals.items():
                if k not in os.environ:
                    os.environ[k] = v
            if db and "DB_CONNECTION_STRING" not in os.environ:
                os.environ["DB_CONNECTION_STRING"] = db
    except Exception:
        pass


load_settings()

SQL = """
-- ── 1. Topic provision map ────────────────────────────────────────────────────
-- Maps each syllabus sub-topic to the specific provisions it covers.
-- Provisions that are in the DB (rpc_codal, civ_codal, etc.) are source='db'.
-- Provisions scraped from external sources are source='scrape'.
CREATE TABLE IF NOT EXISTS bar_topic_provision_map (
    id           SERIAL PRIMARY KEY,
    subject_id   TEXT NOT NULL,          -- 'criminal', 'remedial', 'political', etc.
    roman_num    TEXT NOT NULL,          -- 'I', 'II', 'III'
    sub_letter   TEXT,                   -- 'A', 'B', 'C' (NULL = whole roman topic)
    statute_id   TEXT NOT NULL,          -- 'RPC', 'CIV', 'LABOR', 'FC', 'CONST', 'ROC', 'RCC', or RA/PD/BP number
    provision_id TEXT NOT NULL,          -- article number, section number, or 'general'
    label        TEXT NOT NULL,          -- human-readable e.g. 'Art. 11 – Justifying Circumstances'
    source       TEXT NOT NULL DEFAULT 'db',  -- 'db' | 'scrape' | 'ai'
    scrape_url   TEXT,                   -- LawPhil/eLib URL when source='scrape'
    specific_sections TEXT               -- e.g. 'Secs. 3, 28-41' for partial law retrieval
);

CREATE INDEX IF NOT EXISTS idx_btpm_subject_roman
    ON bar_topic_provision_map (subject_id, roman_num);

-- ── 2. Reviewer topics ────────────────────────────────────────────────────────
-- Stores AI-generated reviewer content per syllabus sub-topic.
-- Status: 'draft' until admin reviews and publishes.
CREATE TABLE IF NOT EXISTS bar_reviewer_topics (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_id       TEXT NOT NULL,
    roman_num        TEXT NOT NULL,
    topic_heading    TEXT NOT NULL,
    sub_letter       TEXT,
    sub_heading      TEXT,
    sort_order       INTEGER NOT NULL DEFAULT 0,  -- global sort within subject
    -- AI-generated content (Gemini 2.5 Pro)
    doctrine_md      TEXT,          -- core doctrine discussion in markdown
    distinctions_md  TEXT,          -- key distinctions / bar traps
    memory_aid       TEXT,          -- mnemonic or framework
    -- Structured data (JSON)
    key_provisions   JSONB,         -- [{statute_id, provision_id, label, text, source_url, source_type}]
    key_cases        JSONB,         -- [{case_id, gr_number, short_title, date, doctrine, bar_trap, significance_category, ponente, division, separate_opinions}]
    bar_questions    JSONB,         -- [{year, text, answer, institution}]
    -- Metadata
    case_cutoff      DATE NOT NULL DEFAULT '2025-06-30',
    status           TEXT NOT NULL DEFAULT 'draft',   -- 'draft' | 'published'
    confidence       TEXT NOT NULL DEFAULT 'db-sourced', -- 'db-sourced' | 'search-grounded' | 'ai-synthesized'
    generated_at     TIMESTAMPTZ,
    generation_model TEXT,
    reviewed_by      TEXT,          -- admin clerk_id who approved
    reviewed_at      TIMESTAMPTZ,
    CONSTRAINT chk_status CHECK (status IN ('draft', 'published')),
    CONSTRAINT chk_confidence CHECK (confidence IN ('db-sourced', 'search-grounded', 'ai-synthesized'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_brt_subject_roman_sub
    ON bar_reviewer_topics (subject_id, roman_num, COALESCE(sub_letter, ''));

CREATE INDEX IF NOT EXISTS idx_brt_subject_status
    ON bar_reviewer_topics (subject_id, status);

-- ── 3. Flags table ────────────────────────────────────────────────────────────
-- Users can flag sections for admin review.
CREATE TABLE IF NOT EXISTS bar_reviewer_flags (
    id           SERIAL PRIMARY KEY,
    topic_id     UUID NOT NULL REFERENCES bar_reviewer_topics(id) ON DELETE CASCADE,
    user_id      TEXT,               -- clerk_id of flagger
    note         TEXT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved     BOOLEAN NOT NULL DEFAULT FALSE,
    resolved_at  TIMESTAMPTZ
);
"""

if __name__ == "__main__":
    conn_str = os.environ.get("DB_CONNECTION_STRING", "")
    if not conn_str:
        print("ERROR: DB_CONNECTION_STRING not set.")
        exit(1)

    try:
        print("Connecting to DB...")
        conn = psycopg2.connect(conn_str)
        conn.autocommit = True
        cur = conn.cursor()
        print("Running migration...")
        cur.execute(SQL)
        print("Done. Tables created:")
        print("  • bar_topic_provision_map")
        print("  • bar_reviewer_topics")
        print("  • bar_reviewer_flags")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Migration failed: {e}")
        exit(1)
