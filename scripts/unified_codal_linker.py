"""
unified_codal_linker.py
========================
Token-Efficient 2-Pass RAG Linker for Philippine Legal Codes.

GenAI: Google AI Studio API key (preferred) or Vertex AI ADC — via ``linker_genai_client``.

How it works:
  PASS 1 (Router): The AI reads the case digest ONCE and returns a list of
                   (code_id, provision id) pairs it thinks are relevant.
  DB Fetch:        The script fetches the FULL TEXT only of those provisions
                   (RPC: ``article_num``; RCC: sections; ROC: ``rule_section_label`` + body text).
  PASS 2 (Granular): The AI re-reads the case digest + the provision texts
                   and identifies the exact 0-based paragraph index.

Dry run (default) prints proposed links only — it does **not** write to
``codal_case_links`` or codal tables. Use ``--commit`` to persist.

This saves tokens vs the old approach (which fed ALL provisions each time) while
still achieving paragraph-level granularity.

Usage:
  python unified_codal_linker.py --limit 5 --commit
  python unified_codal_linker.py --year 2024 --workers 5 --commit
  python unified_codal_linker.py --statutes CIV,LAB,CONST,FAM --limit 10  # optional: other codes

Default statutes are RPC and RCC only. Use ``--statutes`` to add or replace the set
(e.g. ``RPC,ROC`` for Penal Code + Rules of Court).
"""

import os
import re
import sys
import json
import time
from typing import Optional
import argparse
import threading
import psycopg2


def _configure_stdio_utf8() -> None:
    """Windows consoles often use cp1252; avoid UnicodeEncodeError on status output."""
    for stream in (sys.stdout, sys.stderr):
        if stream is None or not hasattr(stream, "reconfigure"):
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError, AttributeError):
            pass


_configure_stdio_utf8()
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool
from concurrent.futures import ThreadPoolExecutor, as_completed
from google import genai

from linker_genai_client import (
    get_linker_genai_client,
    get_linker_model_name,
    get_linker_rate_limiter,
    merge_local_settings_into_env,
)

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
merge_local_settings_into_env()
DB_URL = os.environ.get("DB_CONNECTION_STRING")
if not DB_URL:
    raise RuntimeError("DB_CONNECTION_STRING environment variable is missing. Refusing to connect to fallback.")
MODEL_NAME = get_linker_model_name()
# client is initialised lazily in run() once --vertex-project is known.
client = None
db_pool: ThreadedConnectionPool = None  # type: ignore

# Full registry of supported codals. Default run = all 7.
FULL_CODE_CONFIGS: dict = {
    "CIV": {
        "table": "civ_codal",
        "name": "Civil Code of the Philippines",
        "subject_area": "Civil Law",
    },
    "LAB": {
        "table": "labor_codal",
        "name": "Labor Code of the Philippines",
        "subject_area": "Labor Law",
    },
    "CONST": {
        "table": "consti_codal",
        "name": "1987 Philippine Constitution",
        "subject_area": "Political Law",
        "sort_by_id": True,
    },
    "FAM": {
        "table": "fc_codal",
        "name": "Family Code of the Philippines",
        "subject_area": "Civil Law",
        "provision_id_transform": lambda num: num.split('-')[-1] if '-' in num else num,
    },
    "RPC": {
        "table": "rpc_codal",
        "name": "Revised Penal Code of the Philippines",
        "subject_area": "Criminal Law",
        "where": "book IS NOT NULL",
    },
    "RCC": {
        "table": "rcc_codal",
        "name": "Revised Corporation Code of the Philippines",
        "subject_area": "Corporate Law",
    },
    "ROC": {
        "table": "roc_codal",
        "name": "Rules of Court of the Philippines",
        "subject_area": "Remedial Law",
    },
    "AM-07-9-12-SC": {
        "table": "sc_issuances_codal",
        "name": "Rule on the Writ of Amparo",
        "subject_area": "Remedial Law",
        "where": "statute_id = 'AM-07-9-12-SC'",
    },
    "AM-08-1-16-SC": {
        "table": "sc_issuances_codal",
        "name": "Rule on the Writ of Habeas Data",
        "subject_area": "Remedial Law",
        "where": "statute_id = 'AM-08-1-16-SC'",
    },
    "AM-09-6-8-SC": {
        "table": "sc_issuances_codal",
        "name": "Rules of Procedure for Environmental Cases",
        "subject_area": "Remedial Law",
        "where": "statute_id = 'AM-09-6-8-SC'",
    },
    "AM-01-7-01-SC": {
        "table": "sc_issuances_codal",
        "name": "Rules on Electronic Evidence",
        "subject_area": "Remedial Law",
        "where": "statute_id = 'AM-01-7-01-SC'",
    },
    "CPRA": {
        "table": "sc_issuances_codal",
        "name": "Code of Professional Responsibility and Accountability",
        "subject_area": "Remedial Law",
        "where": "statute_id = 'CPRA'",
    },
    "AM-02-8-13-SC": {
        "table": "sc_issuances_codal",
        "name": "2004 Rules on Notarial Practice",
        "subject_area": "Remedial Law",
        "where": "statute_id = 'AM-02-8-13-SC'",
    },
    "NCJC": {
        "table": "sc_issuances_codal",
        "name": "New Code of Judicial Conduct",
        "subject_area": "Remedial Law",
        "where": "statute_id = 'NCJC'",
    },
    "RA-11642": {
        "table": "sc_issuances_codal",
        "name": "Domestic Administrative Adoption Act",
        "subject_area": "Remedial Law",
        "where": "statute_id = 'RA-11642'",
    },
}

DEFAULT_LINKER_STATUTES: tuple = ("CIV", "LAB", "CONST", "FAM", "RPC", "ROC", "RCC")

# Active set — reassigned at the start of each ``run()`` (default: RPC, RCC).
CODE_CONFIGS: dict = {
    k: FULL_CODE_CONFIGS[k] for k in DEFAULT_LINKER_STATUTES
}

_STATUTE_PROMPT_LINES: dict = {
    "CIV": '  CIV: Civil Code of the Philippines — format: bare article number (e.g. "1306")',
    "LAB": '  LAB: Labor Code of the Philippines — format: bare article number (e.g. "301")',
    "CONST": (
        "  CONST: 1987 Philippine Constitution — format: Article-Section like \"III-1\" "
        '(Article III Section 1), "VIII-15" (Article VIII Section 15)'
    ),
    "FAM": '  FAM: Family Code of the Philippines — format: bare article number (e.g. "36")',
    "RPC": (
        '  RPC: Revised Penal Code — format: bare article number as in the code (e.g. "6", "48")'
    ),
    "RCC": (
        "  RCC: Revised Corporation Code — the Code has **Sections**, not Articles. "
        'Format: bare section number as stored (e.g. "23"); omit the word "Section". '
        'JSON still uses the field name "article" for every code; for RCC its value is the section number.'
    ),
    "ROC": (
        "  ROC: Rules of Court — use the exact **rule_section_label** string as stored in the codal "
        '(typically like "Rule 39, Section 3" with "Rule" and comma; match spacing and numbering to the index). '
        'JSON key remains **"article"**; value is that full label, not a bare section number alone.'
    ),
    "AM-07-9-12-SC": '  AM-07-9-12-SC: Rule on the Writ of Amparo — format: bare section number (e.g. "3")',
    "AM-08-1-16-SC": '  AM-08-1-16-SC: Rule on the Writ of Habeas Data — format: bare section number (e.g. "3")',
    "AM-09-6-8-SC": '  AM-09-6-8-SC: Rules of Procedure for Environmental Cases — format: Rule-Section (e.g. "Rule 1, Section 2")',
    "AM-01-7-01-SC": '  AM-01-7-01-SC: Rules on Electronic Evidence — format: Rule-Section (e.g. "Rule 1, Section 2")',
    "CPRA": '  CPRA: Code of Professional Responsibility and Accountability — format: Canon-Section (e.g. "Canon I, Section 1" or "Canon II, Section 0" for preambles)',
    "AM-02-8-13-SC": '  AM-02-8-13-SC: 2004 Rules on Notarial Practice — format: Rule-Section (e.g. "Rule I, Section 1")',
    "NCJC": '  NCJC: New Code of Judicial Conduct — format: Canon-Section (e.g. "Canon 1, Section 1")',
    "RA-11642": '  RA-11642: Domestic Administrative Adoption Act — format: bare section number (e.g. "5")',
}

_STATUTE_ORDER: tuple = ("CIV", "LAB", "CONST", "FAM", "RPC", "ROC", "RCC", "AM-07-9-12-SC", "AM-08-1-16-SC", "AM-09-6-8-SC", "AM-01-7-01-SC", "CPRA", "AM-02-8-13-SC", "NCJC", "RA-11642")


def _codes_detail_prompt() -> str:
    lines = [
        _STATUTE_PROMPT_LINES[cid]
        for cid in _STATUTE_ORDER
        if cid in CODE_CONFIGS and cid in _STATUTE_PROMPT_LINES
    ]
    return "\n".join(lines)

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def get_db_connection():
    global db_pool
    if db_pool is None:
        db_pool = ThreadedConnectionPool(1, 50, dsn=DB_URL)
    return db_pool.getconn()


def release(conn):
    if db_pool:
        db_pool.putconn(conn)


# ---------------------------------------------------------------------------
# Pre-load article index (article_num + paragraph count, no full text yet)
# ---------------------------------------------------------------------------

def load_article_index() -> dict:
    """
    Returns a nested dict:
        index[code_id][provision_key] = {
            'content': ...,
            'paragraph_count': N,
        }
    For CONST, provision_key is the section_label (e.g. 'SECTION 2') —
    the same value that const.py API sends to the frontend as article_num.
    For other codes, the key is the bare ``article_num`` after stripping labels (e.g. CIV ``1306``).
    RCC uses the same DB column but legally those are **section** numbers.
    ROC uses ``rule_section_label`` as the provision key and ``content_md`` or ``section_content`` as body.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    index: dict = {}

    for code_id, cfg in CODE_CONFIGS.items():
        index[code_id] = {}
        table = cfg["table"]
        where = f"WHERE {cfg['where']}" if "where" in cfg else ""

        if code_id == "ROC":
            cur.execute(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                """,
                (table,),
            )
            roc_cols = {str(r[0]) for r in cur.fetchall()}
            if "section_content" in roc_cols and "content_md" in roc_cols:
                body_expr = (
                    "COALESCE(NULLIF(TRIM(content_md), ''), NULLIF(TRIM(section_content), ''))"
                )
            elif "section_content" in roc_cols:
                body_expr = "NULLIF(TRIM(section_content), '')"
            else:
                body_expr = "NULLIF(TRIM(content_md), '')"
            cur.execute(
                f"""
                SELECT rule_section_label, {body_expr} AS body
                FROM {table} {where}
                """
            )
            for row in cur.fetchall():
                key = str(row[0] or "").strip()
                if not key:
                    continue
                text = str(row[1] or "")
                paragraphs = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
                index[code_id][key] = {
                    "content": text,
                    "paragraph_count": len(paragraphs),
                }
        elif code_id == "CONST":
            # Use raw article_num (e.g. 'III-1') — unique and what const.py stores.
            # section_label ('SECTION 2') is ambiguous (20 dupes across articles).
            cur.execute(
                f"SELECT article_num, content_md FROM {table} {where}"
            )
            for row in cur.fetchall():
                art_num = str(row[0] or "").strip()
                if not art_num:
                    continue
                text = str(row[1] or "")
                paragraphs = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
                index[code_id][art_num] = {
                    "content": text,
                    "paragraph_count": len(paragraphs),
                }
        elif code_id == "FAM":
            # fc_codal uses article_num like 'FC-IX-220'; match FC API key (last segment).
            transform = cfg.get("provision_id_transform", lambda x: x)
            cur.execute(
                f"SELECT article_num, content_md FROM {table} {where}"
            )
            for row in cur.fetchall():
                raw_num = str(row[0] or "").strip()
                provision_key = transform(raw_num)
                text = str(row[1] or "")
                paragraphs = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
                index[code_id][provision_key] = {
                    "content": text,
                    "paragraph_count": len(paragraphs),
                }
        elif code_id in ("AM-07-9-12-SC", "AM-08-1-16-SC", "RA-11642"):
            cur.execute(f"SELECT section_num, content_md FROM {table} {where}")
            for row in cur.fetchall():
                key = str(row[0] or "").strip()
                if not key:
                    continue
                text = str(row[1] or "")
                paragraphs = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
                index[code_id][key] = {
                    "content": text,
                    "paragraph_count": len(paragraphs),
                }
        elif code_id in ("AM-09-6-8-SC", "AM-01-7-01-SC", "CPRA", "AM-02-8-13-SC", "NCJC"):
            cur.execute(f"SELECT group_type, group_num, section_num, content_md FROM {table} {where}")
            for row in cur.fetchall():
                g_type = str(row[0] or "").strip()
                g_num = str(row[1] or "").strip()
                s_num = str(row[2] or "").strip()
                if g_type and g_num:
                    key = f"{g_type} {g_num}, Section {s_num}"
                else:
                    key = s_num
                if not key:
                    continue
                text = str(row[3] or "")
                paragraphs = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
                index[code_id][key] = {
                    "content": text,
                    "paragraph_count": len(paragraphs),
                }
        else:
            cur.execute(f"SELECT article_num, content_md FROM {table} {where}")
            for row in cur.fetchall():
                raw_num = str(row[0])
                clean_num = re.sub(
                    r"^(Article|Section|Art\.)\s+", "", raw_num, flags=re.IGNORECASE
                ).strip()
                text = str(row[1] or "")
                paragraphs = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
                index[code_id][clean_num] = {
                    "content": text,
                    "paragraph_count": len(paragraphs),
                }

    cur.close()
    release(conn)
    return index


def _canonical_provision_key(code_id: str, article_index: dict, art_clean: str) -> Optional[str]:
    """Map model output to index key; ROC labels are matched case-insensitively."""
    bucket = article_index.get(code_id) or {}
    if art_clean in bucket:
        return art_clean
    if code_id in ("ROC", "AM-09-6-8-SC", "AM-01-7-01-SC", "CPRA", "AM-02-8-13-SC", "NCJC"):
        cf = art_clean.casefold()
        for k in bucket:
            if k.casefold() == cf:
                return k
    return None


# ---------------------------------------------------------------------------
# Retry helper — handles 429 RESOURCE_EXHAUSTED from both AI Studio and Vertex
# ---------------------------------------------------------------------------

def _genai_generate_with_retry(prompt: str, max_retries: int = 5) -> str:
    """Call client.models.generate_content with global rate limiting + exponential backoff on 429."""
    get_linker_rate_limiter().acquire()

    delay = 15
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=genai.types.GenerateContentConfig(response_mime_type="application/json"),
            )
            if not response.text:
                raise ValueError("Empty response from API (response.text is None)")
            return response.text
        except Exception as exc:
            msg = str(exc)
            is_rate_limit = "429" in msg or "RESOURCE_EXHAUSTED" in msg
            is_transient = (
                "SSL" in msg or "EOF" in msg
                or "Server disconnected" in msg
                or "Empty response" in msg
                or "ConnectionError" in msg
            )
            if is_rate_limit and attempt < max_retries - 1:
                print(f"    [RATE] 429 — waiting {delay}s before retry {attempt + 2}/{max_retries}…", flush=True)
                time.sleep(delay)
                delay = min(delay * 2, 120)
                continue
            if is_transient and attempt < 3:
                time.sleep(3)
                continue
            raise


# ---------------------------------------------------------------------------
# PASS 1 – Router pass: which code + provision numbers does this case touch?
# ---------------------------------------------------------------------------

PASS1_SCHEMA = """
{
  "hits": [
    {"code_id": "RPC", "article": "6"},
    {"code_id": "ROC", "article": "Rule 39, Section 3"},
    {"code_id": "RCC", "article": "23"}
  ]
}
"""


def pass1_route(case: dict) -> list:
    """
    Ask the AI: 'does this case interpret a provision from any of the configured codes?
    If so, which code_id and provision identifier?'
    Returns a list of dicts: [{'code_id': 'RPC', 'article': '6'}, ...]
    (JSON field remains ``article`` for all codes; RCC: section number; ROC: full rule_section_label.)
    """
    prompt = f"""
You are a Philippine legal expert. Analyse the case digest below and list every
specific provision from these Philippine statutes that this case INTERPRETS or APPLIES
(not just mentions).

AVAILABLE STATUTES AND NUMBERING FORMAT:
{_codes_detail_prompt()}

CASE:
Title: {case.get('short_title', '')}
Facts: {case.get('digest_facts') or 'N/A'}
Issues: {case.get('digest_issues') or 'N/A'}
Doctrine: {case.get('main_doctrine') or ''}
Ratio: {case.get('digest_ratio') or ''}
Ruling: {case.get('digest_ruling') or ''}
Significance: {case.get('digest_significance') or ''}

TASK (CORE CONSIDERATION):
Your PRIMARY basis for identifying the correct statute and provision are the **Issues** and the **Ratio Decidendi**. The Facts and Doctrine provide essential context but the binding legal link is found in the correspondence between the specific legal issues raised and the court's reasoning.

RULES:
- Output ONLY valid code_id values from the list above.
- Use the exact numbering format shown per code (RPC: article numbers; RCC: **section** numbers only — the RCC has no "Articles"; ROC: full **rule_section_label** as listed).
- Each hit must use JSON key **"article"** for every code; for RCC the value is the bare section number string; for ROC the value is the full Rules label (e.g. "Rule 39, Section 3"), not a lone section number.
  Constitution example: "III-2" means Article III, Section 2.
- If no provision from these statutes is interpreted, return {{"hits": []}}

OUTPUT FORMAT (JSON only):
{PASS1_SCHEMA}
"""

    try:
        text = _genai_generate_with_retry(prompt)
        data = json.loads(text)
        return data.get("hits", []) if isinstance(data, dict) else []
    except Exception as exc:
        print(f"    [WARN] PASS-1 error: {exc}", flush=True)
        return []


# ---------------------------------------------------------------------------
# PASS 2 – Granular pass: exact paragraph index given the full provision text
# ---------------------------------------------------------------------------

PASS2_SCHEMA = """
{
  "links": [
    {
      "code_id": "RPC",
      "article": "6",
      "paragraph_index": -1,
      "summary": "..."
    }
  ]
}
"""


def _candidate_heading(code_id: str, art_num: str) -> str:
    """RCC: Section; ROC: rule_section_label as-is; others: Article."""
    if code_id in ("RCC", "AM-07-9-12-SC", "AM-08-1-16-SC", "RA-11642"):
        return f"[{code_id}] Section {art_num}:"
    if code_id in ("ROC", "AM-09-6-8-SC", "AM-01-7-01-SC", "CPRA", "AM-02-8-13-SC", "NCJC"):
        return f"[{code_id}] {art_num}:"
    return f"[{code_id}] Article {art_num}:"


def pass2_granular(case: dict, candidates: list, article_index: dict) -> list:
    """
    For each (code_id, article) candidate, we already have the full text.
    Build one combined prompt for all of them and ask the AI to:
      1. Confirm whether the case really interprets that provision.
      2. Identify the exact 0-based paragraph index (or -1 for general).
      3. Write a concise ruling summary.
    """
    if not candidates:
        return []

    # Build article text block
    article_blocks = []
    for code_id, art_num in candidates:
        entry = article_index[code_id].get(art_num)
        if not entry:
            continue
        article_blocks.append(
            f"{_candidate_heading(code_id, art_num)}\n{entry['content'][:800]}"
        )

    if not article_blocks:
        return []

    articles_section = "\n\n---\n\n".join(article_blocks)

    prompt = f"""
You are a Philippine legal expert finalising a jurisprudence database.

CASE:
Title: {case.get('short_title', '')}
Facts: {case.get('digest_facts') or ''}
Issues: {case.get('digest_issues') or ''}
Doctrine: {case.get('main_doctrine') or ''}
Ratio: {case.get('digest_ratio') or ''}
Ruling: {case.get('digest_ruling') or ''}

CANDIDATE PROVISIONS:
{articles_section}

For EACH candidate provision above:
1. Confirm whether the case truly interprets/applies it (include it only if yes).
2. Identify the exact 0-based paragraph that is discussed, or -1 if the ruling
   is about the provision in general (not a specific paragraph).
   Count paragraph breaks (blank lines) starting from 0.
   **PRIORITY**: Align the case **Issues** and **Ratio** with the specific paragraph of the provision. Use the **Facts** to verify that the application matches the original context.
3. Write a concise one-to-two sentence summary of the holding regarding that provision.

RULES:
- "article" = for RPC/RCC, bare number/string as in the candidate heading (no leading "Article" / "Section" prefix where the heading used Article/Section).
  For **ROC**, "article" must be the **full** provision label exactly as in the bracket line (e.g. "Rule 39, Section 3"), including "Rule" and punctuation as shown.
- "paragraph_index" = integer (-1 for general).

OUTPUT (JSON only):
{PASS2_SCHEMA}
"""

    try:
        text = _genai_generate_with_retry(prompt)
        data = json.loads(text)
        return data.get("links", []) if isinstance(data, dict) else []
    except Exception as exc:
        print(f"    [WARN] PASS-2 error: {exc}", flush=True)
        return []


# ---------------------------------------------------------------------------
# Main per-case worker
# ---------------------------------------------------------------------------

def process_case(case: dict, article_index: dict, dry_run: bool) -> int:
    title = case.get("short_title", str(case["id"]))[:50]

    # ---- PASS 1 ----
    raw_hits = pass1_route(case)
    if not raw_hits:
        return 0

    # Validate hits against index (normalise article numbers)
    valid_candidates = []  # list of (code_id, normalised_art_num)
    for hit in raw_hits:
        code_id = hit.get("code_id", "")
        art_raw = str(hit.get("article", "")).strip()
        art_clean = re.sub(
            r"^(Article|Section|Art\.)\s+", "", art_raw, flags=re.IGNORECASE
        ).strip()

        if code_id not in article_index:
            continue
        canon = _canonical_provision_key(code_id, article_index, art_clean)
        if canon:
            valid_candidates.append((code_id, canon))

    if not valid_candidates:
        return 0

    # ---- PASS 2 ----
    granular = pass2_granular(case, valid_candidates, article_index)
    if not granular:
        return 0

    # Validate and sanitise PASS-2 output
    final_links = []
    for link in granular:
        code_id = link.get("code_id", "")
        art_raw = str(link.get("article", "")).strip()
        art_clean = re.sub(
            r"^(Article|Section|Art\.)\s+", "", art_raw, flags=re.IGNORECASE
        ).strip()

        if code_id not in article_index:
            continue
        canon = _canonical_provision_key(code_id, article_index, art_clean)
        if not canon:
            continue
        entry = article_index[code_id].get(canon)
        if not entry:
            continue

        para_idx = int(link.get("paragraph_index", -1))
        if para_idx >= entry["paragraph_count"]:
            para_idx = -1

        final_links.append({
            "code_id": code_id,
            "provision_id": canon,  # canonical DB / API key
            "paragraph_index": para_idx,
            "summary": str(link.get("summary", ""))[:4000],
            "subject_area": CODE_CONFIGS[code_id]["subject_area"],
        })

    if dry_run:
        for lk in final_links:
            prov = "Sec." if lk["code_id"] == "RCC" else "Art."
            print(
                f"   [DRY] {lk['code_id']} {prov}{lk['provision_id']} "
                f"¶{lk['paragraph_index']}: {lk['summary'][:60]}..."
            )
        return len(final_links)

    # ---- COMMIT ----
    skey = ",".join(sorted(CODE_CONFIGS.keys()))
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Idempotency: delete existing links for this case across all codes
        cur.execute(
            "DELETE FROM codal_case_links WHERE case_id = %s AND statute_id = ANY(%s)",
            (case["id"], list(CODE_CONFIGS.keys())),
        )
        for lk in final_links:
            cur.execute(
                """
                INSERT INTO codal_case_links
                    (case_id, statute_id, provision_id, target_paragraph_index,
                     specific_ruling, subject_area, is_resolved, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, TRUE, NOW())
                """,
                (
                    case["id"],
                    lk["code_id"],
                    lk["provision_id"],
                    lk["paragraph_index"],
                    lk["summary"],
                    lk["subject_area"],
                ),
            )
        # Mark as processed so 0-link cases are not retried
        cur.execute(
            """
            INSERT INTO codal_linker_processed (case_id, statutes_key)
            VALUES (%s, %s) ON CONFLICT DO NOTHING
            """,
            (case["id"], skey),
        )
        conn.commit()
        cur.close()
        print(f"   [saved] {len(final_links)} links -> {title}", flush=True)
    except Exception as exc:
        conn.rollback()
        print(f"   [ERR] DB error for {title}: {exc}", flush=True)
    finally:
        release(conn)

    return len(final_links)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run(
    limit=None,
    start_year=None,
    end_year=None,
    workers=1,
    dry_run=True,
    statutes=None,
    target_ids=None,
    vertex_project: str | None = None,
    vertex_location: str | None = None,
):
    global client
    client = get_linker_genai_client(
        vertex_project=vertex_project,
        vertex_location=vertex_location,
    )
    from linker_genai_client import _vertex_project as _vp
    mode_str = f"Vertex AI (project={_vp})" if _vp else "AI Studio (API key)"

    print("\n" + "=" * 70)
    print(f"  Unified 2-Pass RAG Linker   Mode: {'DRY RUN' if dry_run else 'COMMIT'}")
    if dry_run:
        print("  (Dry run: no writes to codal_case_links or codal body tables.)")
    print(f"  GenAI backend: {mode_str}")
    print(f"  Model: {MODEL_NAME}")

    global CODE_CONFIGS
    if statutes:
        filtered_configs = {
            cid: FULL_CODE_CONFIGS[cid] for cid in statutes if cid in FULL_CODE_CONFIGS
        }
        if not filtered_configs:
            print(f"[ERR] None of the provided statutes {statutes} are configured.")
            return
        CODE_CONFIGS = filtered_configs
    else:
        CODE_CONFIGS = {k: FULL_CODE_CONFIGS[k] for k in DEFAULT_LINKER_STATUTES}
    print(f"[*] Statutes: {', '.join(CODE_CONFIGS.keys())}")
    
    if target_ids:
        print(f"  Target IDs: {len(target_ids)} specific case(s)   Workers: {workers}")
    else:
        range_str = "ALL"
        if start_year and end_year:
            range_str = f"{start_year}-{end_year}"
        elif start_year:
            range_str = f"{start_year}+"
        elif end_year:
            range_str = f"up to {end_year}"
        print(f"  Years: {range_str}   Workers: {workers}")
    print("=" * 70 + "\n")

    # Load provision index once (column name article_num; RCC = sections)
    print("[*] Building provision index from codal tables...")
    article_index = load_article_index()
    total_arts = sum(len(v) for v in article_index.values())
    for cid, arts in article_index.items():
        unit = "sections" if cid == "RCC" else "articles"
        print(f"   {cid}: {len(arts)} {unit}")
    print(f"   Total: {total_arts} provisions indexed\n")

    # Fetch cases
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    query = """
        SELECT id, short_title, main_doctrine, digest_ruling,
               digest_significance, digest_ratio, digest_facts, digest_issues
        FROM sc_decided_cases
        WHERE (main_doctrine IS NOT NULL
               OR digest_ruling IS NOT NULL
               OR digest_ratio IS NOT NULL
               OR digest_issues IS NOT NULL)
    """
    params = []

    if target_ids:
        # Pipeline mode: link only these specific row IDs; bypass year + already-linked filters
        # so freshly digested cases are always processed regardless of existing links.
        placeholders = ",".join(["%s"] * len(target_ids))
        query += f" AND id IN ({placeholders})"
        params.extend(target_ids)
    else:
        if start_year and end_year:
            query += " AND date BETWEEN %s AND %s"
            params += [f"{start_year}-01-01", f"{end_year}-12-31"]
        elif start_year:
            query += " AND date >= %s"
            params += [f"{start_year}-01-01"]
        elif end_year:
            query += " AND date <= %s"
            params += [f"{end_year}-12-31"]

        if not dry_run:
            # Exclude cases already linked OR already processed (0-link) for these statutes
            target_statutes = list(CODE_CONFIGS.keys())
            skey = ",".join(sorted(target_statutes))
            query += """
                AND NOT EXISTS (
                    SELECT 1 FROM codal_case_links
                    WHERE case_id = sc_decided_cases.id
                      AND statute_id = ANY(%s)
                )
                AND NOT EXISTS (
                    SELECT 1 FROM codal_linker_processed
                    WHERE case_id = sc_decided_cases.id
                      AND statutes_key = %s
                )
            """
            params.append(target_statutes)
            params.append(skey)

    query += " ORDER BY id DESC"
    if limit and not target_ids:
        query += " LIMIT %s"
        params.append(limit)

    cur.execute(query, params)
    cases = cur.fetchall()
    cur.close()
    release(conn)

    if not cases:
        print("[ok] No pending cases found.")
        return

    print(f"[*] {len(cases)} cases to analyse\n" + "=" * 70, flush=True)

    total_links = 0
    t0 = time.time()

    if workers > 1:
        # Heartbeat even when zero cases have finished yet (slow Vertex / cold start).
        progress = {"done": 0}
        prog_lock = threading.Lock()
        stop_hb = threading.Event()

        def _heartbeat_loop():
            interval = 30.0
            while not stop_hb.wait(interval):
                with prog_lock:
                    d = progress["done"]
                elapsed = time.time() - t0
                print(
                    f"  [...] heartbeat {elapsed:.0f}s: {d}/{len(cases)} cases finished "
                    f"(workers={workers})",
                    flush=True,
                )

        hb_thread = threading.Thread(target=_heartbeat_loop, daemon=True)
        hb_thread.start()
        try:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futs = {pool.submit(process_case, c, article_index, dry_run): c for c in cases}
                print(
                    f"[*] Pool running: {len(cases)} cases, {workers} workers — "
                    "first [n/total] line may take 1-3 min.",
                    flush=True,
                )
                for i, fut in enumerate(as_completed(futs), 1):
                    c = futs[fut]
                    n = fut.result()
                    total_links += n
                    with prog_lock:
                        progress["done"] = i
                    print(
                        f"  [{i}/{len(cases)}] {c['short_title'][:45]} -> {n} links",
                        flush=True,
                    )
        finally:
            stop_hb.set()
    else:
        for i, case in enumerate(cases, 1):
            print(f"[{i}/{len(cases)}] {case['short_title'][:55]}", flush=True)
            total_links += process_case(case, article_index, dry_run)

    elapsed = time.time() - t0
    print("\n" + "=" * 70)
    print(f"  Cases evaluated : {len(cases)}")
    print(f"  Links created   : {total_links}")
    print(f"  Time elapsed    : {elapsed:.1f}s")
    print("=" * 70)


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------

# All 7 supported codals — used by --all-statutes flag
_ALL_STATUTES = list(FULL_CODE_CONFIGS.keys())  # CIV, LAB, CONST, FAM, RPC, ROC, RCC


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Unified 2-Pass RAG Codal Linker")
    parser.add_argument("--limit", type=int, help="Max cases to process (ignored with --target-ids)")
    parser.add_argument("--year", type=int, help="Filter by case year (ignored with --target-ids)")
    parser.add_argument("--start_year", type=int, help="Filter by start year (ignored with --target-ids)")
    parser.add_argument("--end_year", type=int, help="Filter by end year (ignored with --target-ids)")
    parser.add_argument("--workers", type=int, default=5, help="Parallel workers")
    parser.add_argument("--commit", action="store_true", help="Write to DB (default: dry-run)")
    parser.add_argument(
        "--statutes",
        type=str,
        help=(
            "Comma-separated code IDs (default: RPC,RCC). "
            "e.g. CIV,LAB,CONST,FAM,RPC,ROC,RCC"
        ),
    )
    parser.add_argument(
        "--all-statutes",
        action="store_true",
        help="Shorthand for --statutes CIV,LAB,CONST,FAM,RPC,ROC,RCC (all 7 codals).",
    )
    parser.add_argument(
        "--target-ids",
        type=str,
        dest="target_ids",
        help=(
            "Comma-separated sc_decided_cases.id values to link. "
            "When set, year filters and the already-linked exclusion are bypassed. "
            "Intended for pipeline use after a fresh digest run."
        ),
    )
    parser.add_argument(
        "--vertex-project",
        type=str,
        dest="vertex_project",
        default=None,
        help="Google Cloud project ID for Vertex AI. If omitted, AI Studio API key is used.",
    )
    parser.add_argument(
        "--vertex-location",
        type=str,
        dest="vertex_location",
        default=None,
        help="Vertex AI region. Defaults to GOOGLE_CLOUD_LOCATION env var (global for gemini-3-flash-preview).",
    )
    args = parser.parse_args()

    try:
        # Resolve year range
        start_year = args.start_year
        end_year = args.end_year
        if args.year:
            start_year = args.year
            end_year = args.year

        # Resolve statutes
        if args.all_statutes:
            statutes = _ALL_STATUTES
        elif args.statutes:
            statutes = [s.strip() for s in args.statutes.split(",") if s.strip()]
        else:
            statutes = None

        # Resolve target IDs
        target_ids = None
        if args.target_ids:
            target_ids = [
                int(x.strip()) for x in args.target_ids.split(",") if x.strip()
            ]

        run(
            limit=args.limit,
            start_year=start_year,
            end_year=end_year,
            workers=args.workers,
            dry_run=not args.commit,
            statutes=statutes,
            target_ids=target_ids,
            vertex_project=args.vertex_project,
            vertex_location=args.vertex_location,
        )
    except KeyboardInterrupt:
        print("\n[stopped] Interrupted.")
    finally:
        if db_pool:
            db_pool.closeall()
