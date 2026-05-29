"""
BAR 2026 Reviewer Generation Pipeline
======================================
Generates reviewer content for one subject at a time.
Run from the api/ directory:

    python tools/generate_bar_reviewer.py --subject criminal
    python tools/generate_bar_reviewer.py --subject criminal --dry-run
    python tools/generate_bar_reviewer.py --subject criminal --only I
    python tools/generate_bar_reviewer.py --subject criminal --only-sub I.C
    python tools/generate_bar_reviewer.py --subject criminal --retry-failed
    python tools/generate_bar_reviewer.py --subject criminal --case-cutoff 2024-12-31

Case cutoff: June 30, 2025 (override with --case-cutoff)
AI model: gemini-2.5-pro (all steps)
Status: published (override with --draft)
"""

import os
import sys
import json
import uuid
import time
import logging
import argparse
import psycopg2
from datetime import datetime
from pathlib import Path
from psycopg2.extras import RealDictCursor
from typing import Optional

# ── Path setup ────────────────────────────────────────────────────────────────
API_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = API_DIR.parent / "scripts"
sys.path.insert(0, str(API_DIR))
sys.path.insert(0, str(SCRIPTS_DIR))

from linker_genai_client import get_linker_genai_client, merge_local_settings_into_env
from tools.bar_criminal_map import CRIMINAL_MAP
from tools.bar_remedial_map import REMEDIAL_MAP
from tools.bar_political_map import POLITICAL_MAP
from tools.bar_civil_map import CIVIL_MAP
from tools.bar_labor_map import LABOR_MAP
from tools.bar_commercial_map import COMMERCIAL_MAP

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

DEFAULT_CASE_CUTOFF = "2025-06-30"
BAR_MODEL           = "gemini-2.5-pro"

# Adaptive pacing — starts at BASE_PACE seconds between topics; increases on 429s
BASE_PACE    = 12.0
_pace        = BASE_PACE

SUBJECT_MAPS = {
    "criminal":    CRIMINAL_MAP,
    "remedial":    REMEDIAL_MAP,
    "political":   POLITICAL_MAP,
    "civil":       CIVIL_MAP,
    "labor":       LABOR_MAP,
    "commercial":  COMMERCIAL_MAP,
}

SUBJECT_LABELS = {
    "criminal":   "Criminal Law (10% of Bar)",
    "remedial":   "Remedial Law, Legal and Judicial Ethics, with Practical Exercises (25% of Bar)",
    "political":  "Political Law and Public International Law (15% of Bar)",
    "civil":      "Civil Law and Land Titles and Deeds (20% of Bar)",
    "labor":      "Labor Law and Social Legislation (10% of Bar)",
    "commercial": "Commercial and Taxation Laws (20% of Bar)",
}

_INT_TO_ROMAN = {
    1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI", 7: "VII",
    8: "VIII", 9: "IX", 10: "X", 11: "XI", 12: "XII", 13: "XIII",
    14: "XIV", 15: "XV", 16: "XVI", 17: "XVII", 18: "XVIII",
}


# ── Gemini AI ─────────────────────────────────────────────────────────────────

def _ai_generate(
    prompt: str,
    *,
    response_mime_type: str = "text/plain",
    temperature: float = 0.2,
    max_tokens: int = 8192,
    retries: int = 6,
) -> str:
    """Generate via Vertex AI with adaptive exponential backoff on 429/503."""
    global _pace
    from google import genai
    from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable
    client = get_linker_genai_client()
    cfg = genai.types.GenerateContentConfig(
        response_mime_type=response_mime_type,
        temperature=temperature,
        max_output_tokens=max_tokens,
    )
    for attempt in range(retries):
        try:
            resp = client.models.generate_content(
                model=BAR_MODEL, contents=prompt, config=cfg
            )
            # Success — gradually ease pacing back toward base
            _pace = max(BASE_PACE, _pace * 0.9)
            return resp.text or ""
        except (ResourceExhausted, ServiceUnavailable) as e:
            if attempt == retries - 1:
                raise
            wait = _pace * (2 ** attempt)
            _pace = min(_pace * 1.5, 120.0)   # increase pace ceiling on repeated 429s
            log.warning(
                "Vertex AI 429/503 (attempt %d/%d), retrying in %.0fs: %s",
                attempt + 1, retries, wait, e,
            )
            time.sleep(wait)
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                if attempt == retries - 1:
                    raise
                wait = _pace * (2 ** attempt)
                _pace = min(_pace * 1.5, 120.0)
                log.warning(
                    "Vertex AI rate limit (attempt %d/%d), retrying in %.0fs",
                    attempt + 1, retries, wait,
                )
                time.sleep(wait)
            else:
                raise
    return ""


# ── Settings / DB ─────────────────────────────────────────────────────────────

def load_settings():
    try:
        with open(API_DIR / "local.settings.json") as f:
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


def get_conn():
    cs = os.environ.get("DB_CONNECTION_STRING", "")
    if not cs:
        raise RuntimeError("DB_CONNECTION_STRING not set")
    # TCP keepalives prevent Azure PostgreSQL from silently dropping idle
    # connections during long AI generation calls (which can take 10-40 min).
    # keepalives_idle=60  → send first probe after 60 s of inactivity
    # keepalives_interval=10 → resend every 10 s if no ACK
    # keepalives_count=5  → drop connection after 5 consecutive failures
    return psycopg2.connect(
        cs,
        keepalives=1,
        keepalives_idle=60,
        keepalives_interval=10,
        keepalives_count=5,
    )


def _ensure_conn(conn):
    """Return a live connection, reconnecting if needed."""
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        return conn
    except Exception:
        log.warning("DB connection lost -- reconnecting")
        try:
            conn.close()
        except Exception:
            pass
        return get_conn()


# ── DB provision fetchers ──────────────────────────────────────────────────────

def fetch_rpc_article(cur, article_num: str) -> Optional[str]:
    cur.execute(
        "SELECT article_title, content_md FROM rpc_codal WHERE article_num = %s LIMIT 1",
        (article_num,),
    )
    row = cur.fetchone()
    if not row:
        return None
    title = row["article_title"] or f"Article {article_num}"
    return f"**{title}**\n\n{row['content_md'] or ''}"


def fetch_const_section(cur, provision_id: str) -> Optional[str]:
    cur.execute(
        """SELECT section_label, article_label, content_md FROM consti_codal
           WHERE article_num = %s LIMIT 1""",
        (provision_id,),
    )
    row = cur.fetchone()
    if not row:
        return None
    label = row["section_label"] or row["article_label"] or provision_id
    return f"**{label}**\n\n{row['content_md'] or ''}"


def fetch_civ_article(cur, article_num: str) -> Optional[str]:
    cur.execute(
        "SELECT article_title, content_md FROM civ_codal WHERE article_num = %s LIMIT 1",
        (article_num,),
    )
    row = cur.fetchone()
    if not row:
        return None
    title = row["article_title"] or f"Article {article_num}"
    return f"**{title}**\n\n{row['content_md'] or ''}"


def fetch_fc_article(cur, article_num: str) -> Optional[str]:
    # fc_codal stores article_num as 'FC-1', 'FC-2', etc. Accept bare numbers too.
    candidates = [article_num, f"FC-{article_num}"]
    for candidate in candidates:
        cur.execute(
            "SELECT article_num, content_md FROM fc_codal WHERE article_num = %s LIMIT 1",
            (candidate,),
        )
        row = cur.fetchone()
        if row:
            label = f"Family Code, Article {article_num}"
            return f"**{label}**\n\n{row['content_md'] or ''}"
    return None


def fetch_labor_article(cur, article_num: str) -> Optional[str]:
    cur.execute(
        "SELECT article_title, content_md FROM labor_codal WHERE article_num = %s LIMIT 1",
        (article_num,),
    )
    row = cur.fetchone()
    if not row:
        return None
    title = row["article_title"] or f"Article {article_num}"
    return f"**{title}**\n\n{row['content_md'] or ''}"


def fetch_rcc_article(cur, article_num: str) -> Optional[str]:
    cur.execute(
        "SELECT article_title, content_md FROM rcc_codal WHERE article_num = %s LIMIT 1",
        (article_num,),
    )
    row = cur.fetchone()
    if not row:
        return None
    title = row["article_title"] or f"RCC Article {article_num}"
    return f"**{title}**\n\n{row['content_md'] or ''}"


def fetch_roc_section(cur, provision_id: str) -> Optional[str]:
    """Lookup roc_codal by provision_id like '1-1' (rule_num=1, section_num=1)."""
    parts = provision_id.split("-")
    if len(parts) < 2:
        return None
    try:
        rule_num = int(parts[0])
        section_num = int(parts[1])
    except ValueError:
        return None
    cur.execute(
        """SELECT rule_section_label, section_title, section_content
           FROM roc_codal WHERE rule_num = %s AND section_num = %s LIMIT 1""",
        (rule_num, section_num),
    )
    row = cur.fetchone()
    if not row:
        return None
    label = row["rule_section_label"] or f"Rule {rule_num}, Section {section_num}"
    title = row["section_title"] or ""
    body  = row["section_content"] or ""
    header = f"**{label}**" + (f" — {title}" if title else "")
    return f"{header}\n\n{body}"


def fetch_sc_issuance(cur, statute_id: str, provision_id: str = "general") -> Optional[str]:
    """Fetch from sc_issuances_codal.

    provision_id='general'   → full statute text (all sections concatenated)
    provision_id='canonN'    → sections under Canon N (e.g. 'canon4' → Canon IV or Canon 4)
    provision_id='N'         → single section number N
    """
    if provision_id == "general":
        cur.execute(
            """SELECT group_type, group_num, group_label, section_num, section_title, content_md
               FROM sc_issuances_codal WHERE statute_id = %s ORDER BY sort_order""",
            (statute_id,),
        )
    elif provision_id.lower().startswith("canon"):
        # 'canon4' → match group_num IN ('4', 'IV', 'iv')
        raw_num = provision_id[5:]   # e.g. '4', '6'
        try:
            arabic = int(raw_num)
            roman  = _INT_TO_ROMAN.get(arabic, raw_num)
        except ValueError:
            arabic = None
            roman  = raw_num.upper()
        cur.execute(
            """SELECT group_type, group_num, group_label, section_num, section_title, content_md
               FROM sc_issuances_codal
               WHERE statute_id = %s
                 AND group_type ILIKE 'Canon'
                 AND (group_num = %s OR group_num = %s)
               ORDER BY sort_order""",
            (statute_id, str(arabic) if arabic else roman, roman),
        )
    else:
        cur.execute(
            """SELECT group_type, group_num, group_label, section_num, section_title, content_md
               FROM sc_issuances_codal
               WHERE statute_id = %s AND section_num = %s
               ORDER BY sort_order LIMIT 1""",
            (statute_id, provision_id),
        )

    rows = cur.fetchall()
    if not rows:
        return None

    parts: list[str] = []
    for row in rows:
        header = f"**Sec. {row['section_num']}**"
        if row["section_title"]:
            header += f" — {row['section_title']}"
        parts.append(f"{header}\n\n{row['content_md'] or ''}")

    return "\n\n---\n\n".join(parts)


def _parse_const_provision_id(provision_id: str) -> str:
    """Convert 'art-3-sec-1' → 'III-1' for consti_codal lookup."""
    parts = provision_id.replace("art-", "").split("-sec-")
    if len(parts) == 2:
        try:
            art_roman = _INT_TO_ROMAN.get(int(parts[0]), parts[0].upper())
        except Exception:
            art_roman = parts[0].upper()
        return f"{art_roman}-{parts[1]}"
    return provision_id


# ── AI synthesis for provisions without DB text ────────────────────────────────

def _ai_synthesize_provision(statute_id: str, article_or_section: str, note: str) -> str:
    """
    Search-grounded provision lookup for statutes not in the DB.
    Uses Google Search so the model retrieves actual enacted text from
    authoritative sources (lawphil.net, officialgazette.gov.ph, etc.)
    rather than relying on training-memory recall.
    """
    prompt = f"""You are a Philippine legal research assistant.

TASK: Find and quote the EXACT TEXT of the following Philippine law provision,
as it was in force as of {DEFAULT_CASE_CUTOFF} (the 2026 Bar Exam cutoff date).

STATUTE: {statute_id}
ARTICLE / SECTION: {article_or_section}
CONTEXT NOTE: {note}

Search in this priority order:
1. officialgazette.gov.ph — most authoritative, signed-law text
2. lawphil.net — reliable, includes amendment history
3. chanrobles.com or elibrary.judiciary.gov.ph — fallback

Rules:
- Quote the provision VERBATIM as currently in force (i.e., incorporating all amendments
  enacted on or before {DEFAULT_CASE_CUTOFF}).
- If the provision was amended, state the amending law (e.g., "as amended by RA 10640").
- Provide the exact source URL where you found the text.
- If you cannot find the exact text, say explicitly: "Exact text not found."
- Do NOT add commentary, analysis, or paraphrase.

Return ONLY valid JSON:
{{
  "text": "...(exact statutory text verbatim, or 'Exact text not found.')...",
  "source_note": "...(e.g. 'RA 9165, Sec. 5 as amended by RA 10640')",
  "source_url": "...(exact URL where you found this, e.g. https://lawphil.net/...)"
}}"""
    try:
        from google import genai
        from google.genai import types as genai_types
        client = get_linker_genai_client()
        search_tool = genai_types.Tool(google_search=genai_types.GoogleSearch())
        cfg = genai.types.GenerateContentConfig(
            tools=[search_tool],
            temperature=0.1,
            max_output_tokens=4096,
        )
        raw = ""
        for _attempt in range(3):
            resp = client.models.generate_content(model=BAR_MODEL, contents=prompt, config=cfg)
            # gemini-2.5-pro is a thinking model. When Google Search AFC is
            # active, resp.text can return "" even on a valid response because
            # the actual JSON lives in the non-thought content parts while
            # resp.text may omit them. Extract text parts explicitly.
            raw = resp.text or ""
            if not raw:
                try:
                    raw = "".join(
                        p.text
                        for p in resp.candidates[0].content.parts
                        if hasattr(p, "text") and p.text and not getattr(p, "thought", False)
                    )
                except Exception:
                    pass
            raw = raw.strip()
            if raw:
                break
            log.warning(
                "  Search-grounded synthesis: empty response for %s %s (attempt %s/3)",
                statute_id, article_or_section, _attempt + 1,
            )
            time.sleep(2 ** _attempt)  # 1s, 2s, 4s back-off

        # Strip markdown fences if model wraps the JSON
        if raw.startswith("```"):
            raw = raw.split("```")[-2] if raw.count("```") >= 2 else raw
            raw = raw.lstrip("json").strip()
        if not raw:
            raise ValueError("Model returned empty response after 3 attempts")
        data = json.loads(raw)
        text     = data.get("text", "")
        note_out = data.get("source_note", "search-grounded")
        src_url  = data.get("source_url", "")
        if text and "not found" not in text.lower():
            url_line = f"\n\n*Source: {src_url}*" if src_url else ""
            log.info("  Search-grounded: %s %s — %s", statute_id, article_or_section, src_url or "no URL")
            return f"[{note_out} — search-grounded]{url_line}\n\n{text}"
        log.warning("  Search could not find exact text for %s %s", statute_id, article_or_section)
    except Exception as e:
        log.warning("  Search-grounded synthesis failed for %s %s: %s", statute_id, article_or_section, e)
    return f"[Provision text not found in DB or via search: {statute_id} {article_or_section}]"


# ── Case fetcher ───────────────────────────────────────────────────────────────

def fetch_cases_for_topic(
    cur, subject_id: str, provisions: list, case_cutoff: str,
    sub_heading_kw: str = "",
) -> list:
    """
    Fetch ALL relevant cases for this topic — no cap.
    Priority: En Banc > Gaerlan > Landmark > recent date.
    Uses a subquery to satisfy DISTINCT + ORDER BY in PostgreSQL.
    Falls back to keyword search on sub_heading if no linked provisions.
    """
    # Collect DB provision pairs that have codal_case_links
    # Include both "db" and "inline" sources — inline provisions have real
    # statute/provision IDs and may have codal_case_links inserted manually.
    linked_pairs = [
        (p["statute_id"], p["provision_id"])
        for p in provisions
        if p.get("source") in ("db", "inline")
        and p.get("statute_id") in ("RPC", "CONST", "ROC", "CIV", "FC", "LABOR", "RCC", "LGC")
        and p.get("provision_id")
    ]

    ORDER_EXPR = """
        CASE WHEN c.division = 'En Banc' THEN 0 ELSE 1 END        AS p1,
        CASE WHEN c.ponente ILIKE '%%Gaerlan%%' THEN 0 ELSE 1 END  AS p2,
        CASE WHEN c.significance_category IN
             ('NEW DOCTRINE','ABANDONMENT','MODIFICATION')
             THEN 0 ELSE 1 END                                      AS p3
    """

    SELECT_COLS = """
        c.id, c.short_title, c.case_number, c.date,
        c.main_doctrine, c.digest_significance, c.significance_category,
        c.ponente, c.division, c.separate_opinions
    """

    if linked_pairs:
        placeholders = " OR ".join(
            ["(l.statute_id = %s AND l.provision_id = %s)"] * len(linked_pairs)
        )
        params = []
        for stat, prov in linked_pairs:
            params.extend([stat, prov])
        params.extend([case_cutoff])

        cur.execute(
            f"""SELECT id, short_title, case_number, date,
                       main_doctrine, digest_significance, significance_category,
                       ponente, division, separate_opinions
                FROM (
                  SELECT DISTINCT ON (c.id)
                         {SELECT_COLS},
                         l.specific_ruling,
                         {ORDER_EXPR}
                  FROM sc_decided_cases c
                  JOIN codal_case_links l ON l.case_id = c.id
                  WHERE ({placeholders})
                    AND c.date <= %s
                    AND c.main_doctrine IS NOT NULL
                    AND c.significance_category IS NOT NULL
                ) sub
                ORDER BY p1, p2, p3, date DESC""",
            params,
        )
        rows = list(cur.fetchall())
        if rows:
            return rows

    # Fallback: keyword search on sub_heading, then subject-wide (capped at 40)
    # sub_heading is passed as a kwarg by the caller if available
    kw = sub_heading_kw or subject_id
    cur.execute(
        f"""SELECT id, short_title, case_number, date,
                   main_doctrine, digest_significance, significance_category,
                   ponente, division, separate_opinions
            FROM (
              SELECT DISTINCT ON (c.id)
                     {SELECT_COLS},
                     {ORDER_EXPR}
              FROM sc_decided_cases c
              WHERE (c.subject ILIKE %s OR c.main_doctrine ILIKE %s)
                AND c.date <= %s
                AND c.main_doctrine IS NOT NULL
                AND c.significance_category IS NOT NULL
            ) sub
            ORDER BY p1, p2, p3, date DESC
            LIMIT 40""",
        (f"%{subject_id}%", f"%{kw[:40]}%", case_cutoff),
    )
    return list(cur.fetchall())


def fetch_db_case_by_gr(cur, gr_number: str, case_cutoff: str) -> Optional[dict]:
    """Fetch a specific case by G.R. number for db_case provisions."""
    gr_bare = gr_number.replace("GR-", "")
    cur.execute(
        """SELECT id, short_title, case_number, date, main_doctrine,
                  digest_significance, significance_category, ponente, division,
                  separate_opinions
           FROM sc_decided_cases
           WHERE case_number ILIKE %s AND date <= %s
           LIMIT 1""",
        (f"%{gr_bare}%", case_cutoff),
    )
    return cur.fetchone()


# ── Question fetcher ───────────────────────────────────────────────────────────

def fetch_bar_questions(cur, subject_id: str, sub_heading: str) -> list:
    # Use first 60 chars of sub_heading to avoid over-constraining the ILIKE
    heading_kw = sub_heading[:60]
    cur.execute(
        """SELECT q.year, q.text, a.text AS answer, a.institution
           FROM questions q
           LEFT JOIN answers a ON a.question_id = q.id
           WHERE q.subject ILIKE %s
             AND (q.sub_topic ILIKE %s OR q.sub_topic IS NULL)
           ORDER BY q.year DESC
           LIMIT 10""",
        (f"%{subject_id.replace('_', ' ')}%", f"%{heading_kw}%"),
    )
    return list(cur.fetchall())


# ── Prompt builders ────────────────────────────────────────────────────────────

def _topic_display(topic: dict) -> str:
    heading = topic.get("sub_heading") or topic.get("heading") or topic.get("topic_heading", "")
    detail  = topic.get("detail", "")
    base    = f"{topic['roman_num']}.{topic.get('sub_letter') or ''} -- {heading}"
    return f"{base}\n{detail}" if detail else base


def build_doctrine_prompt(
    topic: dict,
    enriched_provisions: list,
    cases: list,
    subject_id: str,
) -> str:
    provisions_block = "\n\n---\n\n".join(
        f"[{p.get('label') or p.get('note') or p.get('provision_id') or p.get('url', 'provision')}]\n"
        f"{p.get('text') or '[text not available]'}"
        for p in enriched_provisions
    ) or "No statutory provisions available."

    cases_block = "\n\n".join(
        f"CASE: {c['short_title']} | {c['case_number']} | {c['date']} | {c['division']}\n"
        f"PONENTE: {c['ponente']}\n"
        f"DOCTRINE: {c['main_doctrine']}\n"
        f"SIGNIFICANCE: {c.get('significance_category', 'N/A')}\n"
        f"BAR TRAP: {c.get('digest_significance', '')}"
        for c in cases
    ) or "No linked cases available for this topic."

    subject_label = SUBJECT_LABELS.get(subject_id, subject_id.title())
    detail_block  = topic.get("detail", "").strip()
    syllabus_section = (
        f"\nSYLLABUS COVERAGE (every sub-item below MUST be addressed in your doctrine):\n{detail_block}\n"
        if detail_block else ""
    )

    return f"""You are a Senior Bar Review Lecturer and Philippine legal scholar.

TASK: Write a comprehensive, exam-ready reviewer section for the 2026 Philippine Bar Exam.

TOPIC: {topic['roman_num']}.{topic.get('sub_letter') or ''} -- {topic.get('sub_heading') or topic.get('heading') or topic.get('topic_heading', '')}
SUBJECT: {subject_label}
CASE CUTOFF: {DEFAULT_CASE_CUTOFF}{syllabus_section}

STATUTORY BASIS (use ONLY the following; do not introduce other provisions):
{provisions_block}

LINKED CASES (use ONLY the following; do not invent cases):
{cases_block}

OUTPUT RULES:
1. doctrine_md: 4-8 paragraphs. Extract and organize rules EXCLUSIVELY from the statutory texts
   and case doctrines provided above. Strict constraints:
   - Statutory rules: paraphrase or quote the provision text; cite the article/section number.
   - Case-derived rules: use only the exact main_doctrine text supplied for each case above.
     You MAY cite a case by name ONLY if it appears in the LINKED CASES list above.
     NEVER cite a case not in that list — do not add cases from your training knowledge.
   - PHANTOM CASE BLOCKLIST — these titles are known hallucinations or are real cases whose
     doctrines are UNRELATED to Remedial Law. If any of them appear in your draft, DELETE them:
       * Suyat v. Court of Appeals — real doctrine: Ombudsman/COA jurisdiction; NOT certiorari, disbarment, or remedial rules
       * Gonzales v. Geronimo — frequently fabricated citation; NO reliable Remedial Law doctrine
       * Bernasconi v. Demaisip — frequently fabricated citation; NO reliable Remedial Law doctrine
       * Amad v. Commission on Elections — real doctrine: nuisance candidates; NOT contempt, injunctions, or procedure
       * Development Bank v. Commission on Audit — real doctrine: GFI salary authority; NOT speedy disposition or procedural rules
       * Mangudadatu v. Commission on Elections — real doctrine: election protest procedure; NOT succession or civil procedure
       * Yap v. Gonzales — frequently fabricated; verify before use; if not in LINKED CASES above, delete
       * OCA v. Reyes / Office of the Court Administrator v. Reyes — frequently fabricated; delete if not in LINKED CASES above
       * Comamo v. People — frequently fabricated; delete if not in LINKED CASES above
       * OCA v. Villavicencio-Olan — frequently fabricated; delete if not in LINKED CASES above
       * Roque v. De Villa — frequently fabricated; delete if not in LINKED CASES above
       * Docena-Caspe v. Bugtas — frequently fabricated; delete if not in LINKED CASES above
       * Garcia v. Tehano-Ang — frequently fabricated; delete if not in LINKED CASES above
       * Usama v. Tomarong — frequently fabricated; delete if not in LINKED CASES above
       * Almonte v. People — frequently fabricated; delete if not in LINKED CASES above
     Any case in your draft that is NOT in the LINKED CASES section above must be removed entirely.
   - DO NOT write any principle, exception, qualification, or rule not explicitly present in the
     materials above. If it is not in the texts, do not write it.
   - If source material is sparse, write shorter doctrine — do not pad with invented rules.
   - If a gap exists, write: "[Topic area] -- no source material in database."
2. distinctions_md: 3-6 bullet points covering the most exam-tested confusions and nuances.
   Every distinction must be directly traceable to the statutory texts or case doctrines above.
   Do not add distinctions from general legal knowledge not present in the materials.
3. memory_aid: One short mnemonic, acronym, or framework (max 8 words or steps).
   Must reflect only rules established by the provided materials above.
4. key_statutes: Array of the 3-7 most critical statutes/articles for this topic.
   Each entry: {{"label": "Art. 11, RPC", "note": "Justifying circumstances -- enumerate all 6"}}
5. synthetic_bar_q: ONE exam-style Bar question (plain string) testing a key distinction in
   this topic, followed immediately by "SUGGESTED ANSWER:" and the model answer — all in one
   string. Base the question and answer only on rules from the materials above.
   Only include if fewer than 2 real bar questions were provided. If not needed, return null.
   IMPORTANT: this must be a plain JSON string, NOT an object or nested JSON.

RETURN ONLY valid JSON (no markdown fences, no trailing commas):
{{
  "doctrine_md": "...",
  "distinctions_md": "...",
  "memory_aid": "...",
  "key_statutes": [{{"label": "...", "note": "..."}}],
  "synthetic_bar_q": null
}}"""


def build_batch_connector_prompt(cases: list, sub_heading: str) -> str:
    cases_json = json.dumps(
        [
            {
                "idx": i,
                "short_title": c["short_title"],
                "case_number": c.get("case_number", ""),
                "date": str(c.get("date", "")),
                "doctrine": c["main_doctrine"],
                "significance": c.get("significance_category", ""),
            }
            for i, c in enumerate(cases)
        ],
        ensure_ascii=False,
    )

    return f"""You are a Philippine Bar review assistant.

TASK: For each case below, write ONE concise sentence (max 35 words) explaining why it is
relevant to the bar exam topic "{sub_heading}". Also identify any bar trap (a common
misconception or frequently-tested nuance) that the case illustrates.

Base your answer ONLY on the doctrine provided. Do NOT add information not in the doctrine.

CASES (JSON array):
{cases_json}

Return ONLY a valid JSON array with one object per case, in the same order:
[
  {{
    "idx": 0,
    "relevance": "...",
    "bar_trap": "..."
  }},
  ...
]"""


def build_verification_prompt(
    topic: dict, doctrine_md: str, cases: list, subject_id: str
) -> str:
    cases_block = "\n".join(
        f"- {c['short_title']} ({c.get('case_number','')}) | {c['main_doctrine'][:350]}"
        for c in cases
    ) or "None"
    return f"""You are a Philippine legal scholar reviewing AI-generated bar reviewer content.

TOPIC: {_topic_display(topic)}
SUBJECT: {SUBJECT_LABELS.get(subject_id, subject_id.title())}

GENERATED DOCTRINE:
{doctrine_md}

VERIFIED CASES (short_title | first 180 chars of main_doctrine):
{cases_block}

KNOWN PHANTOM CASES — these real cases are frequently misused with wrong doctrines.
Treat any citation to these as hallucinated UNLESS the verified doctrine in the list
above EXACTLY matches the principle being cited:
- "Suyat v. Court of Appeals" — real doctrine: Ombudsman/COA jurisdiction, NOT certiorari or disbarment rules
- "Amad v. Commission on Elections" — real doctrine: nuisance candidates, NOT contempt or injunctions
- "Development Bank v. Commission on Audit" — real doctrine: GFI salary authority, NOT speedy disposition
- "Mangudadatu v. Commission on Elections" — real doctrine: election protest procedure, NOT succession rules
- "Gonzales v. Geronimo" — frequently fabricated; verify against the list before accepting
- "Bernasconi v. Demaisip" — frequently fabricated; verify against the list before accepting
- "Yap v. Gonzales" — frequently fabricated; treat as hallucinated if not in VERIFIED CASES
- "OCA v. Reyes" / "Office of the Court Administrator v. Reyes" — frequently fabricated; treat as hallucinated if not in VERIFIED CASES
- "Comamo v. People" — frequently fabricated; treat as hallucinated if not in VERIFIED CASES
- "OCA v. Villavicencio-Olan" — frequently fabricated; treat as hallucinated if not in VERIFIED CASES
- "Roque v. De Villa" — frequently fabricated; treat as hallucinated if not in VERIFIED CASES
- "Docena-Caspe v. Bugtas" — frequently fabricated; treat as hallucinated if not in VERIFIED CASES
- "Garcia v. Tehano-Ang" — frequently fabricated; treat as hallucinated if not in VERIFIED CASES
- "Usama v. Tomarong" — frequently fabricated; treat as hallucinated if not in VERIFIED CASES
- "Almonte v. People" — frequently fabricated; treat as hallucinated if not in VERIFIED CASES

TASK:
1. Find every case cited by name in the doctrine.
2. For each cited case, check if its short_title appears in the VERIFIED CASES list.
   - If it DOES appear → verify the cited principle matches the provided doctrine snippet.
     If the principle does not match what the verified doctrine says, treat it as misused
     (hallucinated). Otherwise leave it as-is.
   - If it does NOT appear → it is hallucinated. Try to find a VERIFIED CASE above whose
     doctrine covers the same legal principle. If found, replace the hallucinated name with
     the verified case's short_title. If no verified case covers that principle, remove the
     citation entirely (keep the legal rule, just drop the fake case attribution).
3. Flag any legal principle that cannot be traced to the verified cases or statutory texts
   (i.e., an uninstructed rule added from general AI knowledge). Remove it.
4. Do NOT flag omissions — the doctrine is intentionally limited to what the DB provides.

Return ONLY valid JSON:
{{
  "hallucinated_cases": ["...(original hallucinated name)..."],
  "replacements": {{"HallucinatedName": "ReplacementVerifiedName or null if removed"}},
  "issues": ["...(other problems found)..."],
  "verdict": "pass" or "flag",
  "corrected_doctrine_md": "...(full corrected text with replacements applied, or null if no changes needed)..."
}}"""


# ── Core generation ────────────────────────────────────────────────────────────

def generate_topic(
    conn,
    topic: dict,
    subject_id: str,
    case_cutoff: str,
    dry_run: bool = False,
    publish: bool = True,
) -> dict:
    cur = conn.cursor(cursor_factory=RealDictCursor)
    roman         = topic["roman_num"]
    sub_letter    = topic.get("sub_letter")
    _heading      = topic.get("heading", "")
    topic_heading = topic.get("topic_heading") or _heading
    sub_heading   = topic.get("sub_heading") or _heading
    provisions    = topic.get("provisions", [])

    log.info("=" * 60)
    log.info("Topic %s.%s -- %s", roman, sub_letter or "", sub_heading)

    # ── Step 1: Gather provision texts (DB first → AI synthesis) ──────────────
    enriched_provisions = []
    confidence = "db-sourced"
    db_hit_count = 0
    total_count  = 0

    for prov in provisions:
        source = prov.get("source", "")
        total_count += 1

        if source == "db_case":
            continue  # handled in Step 2

        if source == "db":
            statute = prov.get("statute_id", "")
            pid     = prov.get("provision_id", "")
            label   = prov.get("label") or pid

            if statute == "RPC":
                text = fetch_rpc_article(cur, pid)
            elif statute == "CONST":
                text = fetch_const_section(cur, pid)
            elif statute == "ROC":
                text = fetch_roc_section(cur, pid)
            elif statute == "CIV":
                text = fetch_civ_article(cur, pid)
            elif statute == "FC":
                text = fetch_fc_article(cur, pid)
            elif statute == "LABOR":
                text = fetch_labor_article(cur, pid)
            elif statute == "RCC":
                text = fetch_rcc_article(cur, pid)
            else:
                # SC issuances and special statutes stored in sc_issuances_codal
                text = fetch_sc_issuance(cur, statute, pid)

            if text:
                db_hit_count += 1
                enriched_provisions.append({**prov, "label": label, "text": text})
            else:
                log.warning("  DB miss: %s %s -- falling back to AI synthesis", statute, pid)
                synth = _ai_synthesize_provision(
                    statute, label, prov.get("note", "")
                ) if not dry_run else f"[dry-run AI synthesis: {statute} {pid}]"
                enriched_provisions.append({**prov, "label": label, "text": synth})
                if confidence == "db-sourced":
                    confidence = "mixed"

        elif source == "const":
            raw_id   = prov.get("provision_id", "")
            db_key   = _parse_const_provision_id(raw_id)
            label    = prov.get("label") or db_key
            text     = fetch_const_section(cur, db_key)
            if text:
                db_hit_count += 1
                enriched_provisions.append({**prov, "label": label, "text": text})
            else:
                log.warning("  DB miss: CONST %s -- falling back to AI synthesis", db_key)
                synth = _ai_synthesize_provision(
                    "CONST", label, prov.get("note", "")
                ) if not dry_run else f"[dry-run AI synthesis: CONST {db_key}]"
                enriched_provisions.append({**prov, "label": label, "text": synth})
                if confidence == "db-sourced":
                    confidence = "mixed"

        elif source == "rpc":
            pid   = prov.get("provision_id", "")
            label = prov.get("label") or f"RPC Art. {pid}"
            text  = fetch_rpc_article(cur, pid)
            if text:
                db_hit_count += 1
                enriched_provisions.append({**prov, "label": label, "text": text})
            else:
                log.warning("  DB miss: RPC %s -- falling back to AI synthesis", pid)
                synth = _ai_synthesize_provision(
                    "RPC", label, prov.get("note", "")
                ) if not dry_run else f"[dry-run AI synthesis: RPC {pid}]"
                enriched_provisions.append({**prov, "label": label, "text": synth})
                if confidence == "db-sourced":
                    confidence = "mixed"

        elif source == "inline":
            # Pre-supplied statutory text — use directly, no DB or AI call needed.
            # The map entry must have a "text" field with the actual provision text.
            label = prov.get("label") or prov.get("note", "")
            text  = prov.get("text", "")
            db_hit_count += 1
            enriched_provisions.append({**prov, "label": label, "text": text})

        elif source in ("roc", "statute", "lawphil", "scrape", "ai"):
            # All non-DB sources → AI synthesis (no scraping)
            statute_id = prov.get("statute_id", source.upper())
            article    = prov.get("provision_id") or prov.get("url", "")
            note       = prov.get("note", "") or prov.get("label", "")
            label      = prov.get("label") or note or article

            if source == "ai":
                # Use search-grounded synthesis (Gemini 2.5 Pro + Google Search)
                # so these provisions get real statutory text rather than a placeholder.
                if not dry_run:
                    synth = _ai_synthesize_provision(statute_id, article or label, note)
                else:
                    synth = f"[dry-run AI synthesis: {statute_id} {article}]"
                confidence = "ai-synthesized"
            else:
                if not dry_run:
                    synth = _ai_synthesize_provision(statute_id, article or label, note)
                else:
                    synth = f"[dry-run AI synthesis: {statute_id} {article}]"
                if confidence == "db-sourced":
                    confidence = "mixed"

            enriched_provisions.append({**prov, "label": label, "text": synth})

        else:
            label = prov.get("label") or prov.get("provision_id", source)
            enriched_provisions.append({
                **prov,
                "label": label,
                "text": f"[Unknown source type: {source}]",
            })

    if total_count > 0 and db_hit_count == 0:
        confidence = "ai-synthesized"

    log.info(
        "  Provisions: %d total | %d from DB | confidence=%s",
        total_count, db_hit_count, confidence,
    )

    # ── Step 2: Fetch cases (all relevant, no cap on linked; capped on fallback) ─
    cases = fetch_cases_for_topic(
        cur, subject_id, provisions, case_cutoff, sub_heading_kw=sub_heading
    )

    # Inject explicitly cited cases (db_case source), deduplicated
    existing_ids = {c["id"] for c in cases}
    for prov in provisions:
        if prov.get("source") == "db_case":
            specific = fetch_db_case_by_gr(cur, prov["provision_id"], case_cutoff)
            if specific and specific["id"] not in existing_ids:
                cases.insert(0, specific)
                existing_ids.add(specific["id"])

    log.info("  Cases found: %d", len(cases))

    # Top cases used for AI prompts (capped so prompts stay manageable).
    # ALL cases are still stored in key_cases for display — only the AI calls
    # use the capped slice. Cases are already sorted by priority (En Banc > Gaerlan > Landmark).
    PROMPT_CASE_CAP = 30
    cases_for_prompt = cases[:PROMPT_CASE_CAP]

    # ── Step 3: Batch case connectors (ONE AI call returns JSON array) ─────────
    cases_with_relevance = []
    if not dry_run and cases_for_prompt:
        connector_map = {}
        # Chunk into batches of 15 to stay within safe JSON output size
        CHUNK = 15
        for chunk_start in range(0, len(cases_for_prompt), CHUNK):
            chunk = cases_for_prompt[chunk_start: chunk_start + CHUNK]
            try:
                raw = _ai_generate(
                    build_batch_connector_prompt(chunk, sub_heading),
                    response_mime_type="application/json",
                    max_tokens=8192,
                )
                # Primary parse
                try:
                    chunk_data = json.loads(raw)
                except json.JSONDecodeError:
                    # Repair: truncate to the last complete object in the array
                    last_brace = raw.rfind("},")
                    if last_brace != -1:
                        repaired = raw[:last_brace + 1] + "]"
                        try:
                            chunk_data = json.loads(repaired)
                            log.warning(
                                "  Batch connector JSON repaired (cases %d-%d): truncated to %d items",
                                chunk_start, chunk_start + len(chunk) - 1, len(chunk_data),
                            )
                        except json.JSONDecodeError:
                            chunk_data = []
                            log.warning(
                                "  Batch connector JSON unrecoverable (cases %d-%d) -- using empty relevance",
                                chunk_start, chunk_start + len(chunk) - 1,
                            )
                    else:
                        chunk_data = []
                        log.warning(
                            "  Batch connector JSON unrecoverable (cases %d-%d) -- using empty relevance",
                            chunk_start, chunk_start + len(chunk) - 1,
                        )
                for d in chunk_data:
                    if isinstance(d, dict) and "idx" in d:
                        connector_map[chunk_start + d["idx"]] = d
            except Exception as e:
                log.warning(
                    "  Batch connector failed (cases %d-%d): %s -- using empty relevance",
                    chunk_start, chunk_start + len(chunk) - 1, e,
                )
    else:
        connector_map = {}

    for i, case in enumerate(cases_for_prompt):
        sep_ops = case.get("separate_opinions")
        if isinstance(sep_ops, str):
            try:
                sep_ops = json.loads(sep_ops)
            except Exception:
                sep_ops = []

        connector = connector_map.get(i, {})
        cases_with_relevance.append({
            "case_id":               str(case["id"]),
            "gr_number":             case.get("case_number", ""),
            "short_title":           case.get("short_title", ""),
            "date":                  str(case.get("date", "")),
            "ponente":               case.get("ponente", ""),
            "division":              case.get("division", ""),
            "main_doctrine":         case.get("main_doctrine", ""),
            "bar_trap":              connector.get("bar_trap") or case.get("digest_significance", ""),
            "significance_category": case.get("significance_category", ""),
            "relevance_to_topic":    connector.get("relevance", "[dry-run]" if dry_run else ""),
            "separate_opinions":     sep_ops or [],
        })

    # ── Step 4: Fetch past bar questions + prepare synthetic fallback ──────────
    questions = fetch_bar_questions(cur, subject_id, sub_heading)
    bar_questions = [
        {
            "year":        row["year"],
            "text":        row["text"],
            "answer":      row["answer"],
            "institution": row["institution"],
        }
        for row in questions
    ]

    # ── Step 5: Generate doctrine + distinctions + key_statutes ───────────────
    if dry_run:
        doctrine_md     = "[dry-run doctrine]"
        distinctions_md = "[dry-run distinctions]"
        memory_aid      = "[dry-run mnemonic]"
        key_statutes    = []
        synthetic_q     = None
    else:
        prompt = build_doctrine_prompt(topic, enriched_provisions, cases_for_prompt, subject_id)
        try:
            raw  = _ai_generate(
                prompt,
                response_mime_type="application/json",
                temperature=0.2,
                max_tokens=32768,
            )
            data            = json.loads(raw)
            doctrine_md     = data.get("doctrine_md", "")
            distinctions_md = data.get("distinctions_md", "")
            memory_aid      = data.get("memory_aid", "")
            key_statutes    = data.get("key_statutes") or []
            synthetic_q     = data.get("synthetic_bar_q")
        except Exception as e:
            log.error("  Doctrine generation failed: %s", e)
            doctrine_md     = f"[Generation error: {e}]"
            distinctions_md = ""
            memory_aid      = ""
            key_statutes    = []
            synthetic_q     = None
            confidence      = "ai-synthesized"

        # Append synthetic question if real questions are scarce
        if synthetic_q and len(bar_questions) < 2:
            # Normalise: AI sometimes returns a dict instead of a plain string
            if isinstance(synthetic_q, dict):
                synth_text   = synthetic_q.get("question") or synthetic_q.get("text") or ""
                synth_answer = synthetic_q.get("answer") or synthetic_q.get("suggested_answer")
            else:
                synth_text   = synthetic_q
                synth_answer = None
                sep_idx = synth_text.upper().find("SUGGESTED ANSWER:")
                if sep_idx != -1:
                    synth_answer = synth_text[sep_idx:].strip()
                    synth_text   = synth_text[:sep_idx].strip()
            if synth_text:
                bar_questions.append({
                    "year":        "2026 (synthetic)",
                    "text":        synth_text,
                    "answer":      synth_answer,
                    "institution": "AI-generated",
                })

        # ── Verification pass ─────────────────────────────────────────────────
        if doctrine_md and not doctrine_md.startswith("["):
            try:
                v_raw  = _ai_generate(
                    build_verification_prompt(topic, doctrine_md, cases_for_prompt, subject_id),
                    response_mime_type="application/json",
                    max_tokens=8192,
                )
                v_data = json.loads(v_raw)
                if v_data.get("verdict") == "flag":
                    issues = v_data.get("issues", [])
                    if issues:
                        log.warning("  Verification flagged issues: %s", "; ".join(issues))
                    hallucinated = v_data.get("hallucinated_cases", [])
                    if hallucinated:
                        log.warning("  Hallucinated cases: %s", hallucinated)
                    replacements = v_data.get("replacements", {})
                    if replacements:
                        for fake, real in replacements.items():
                            if real:
                                log.info("  Replaced: '%s' → '%s'", fake, real)
                            else:
                                log.info("  Removed (no match): '%s'", fake)
                    corrected = v_data.get("corrected_doctrine_md")
                    if corrected:
                        doctrine_md = corrected
                        log.info("  Verification applied correction.")
            except Exception as e:
                log.warning("  Verification pass failed (non-fatal): %s", e)

    # ── Step 6: Build key_provisions payload ──────────────────────────────────
    key_provisions = [
        {
            "statute_id":   p.get("statute_id", ""),
            "provision_id": p.get("provision_id", ""),
            "label":        p.get("label") or p.get("note", ""),
            "text":         p.get("text", ""),
            "source_url":   p.get("url") or p.get("scrape_url", ""),
            "source_type":  p.get("source", ""),
        }
        for p in enriched_provisions
    ]

    return {
        "subject_id":       subject_id,
        "roman_num":        roman,
        "topic_heading":    topic_heading,
        "sub_letter":       sub_letter,
        "sub_heading":      sub_heading,
        "sort_order":       topic.get("sort_order", 0),
        "doctrine_md":      doctrine_md,
        "distinctions_md":  distinctions_md,
        "memory_aid":       memory_aid,
        "key_provisions":   json.dumps(key_provisions, ensure_ascii=False),
        "key_cases":        json.dumps(cases_with_relevance, ensure_ascii=False),
        "bar_questions":    json.dumps(bar_questions, ensure_ascii=False),
        "key_statutes":     json.dumps(key_statutes, ensure_ascii=False),
        "case_cutoff":      case_cutoff,
        "status":           "published" if publish else "draft",
        "confidence":       confidence,
        "generation_model": BAR_MODEL,
    }


# ── Upsert to DB ───────────────────────────────────────────────────────────────

UPSERT_SQL = """
INSERT INTO bar_reviewer_topics
    (id, subject_id, roman_num, topic_heading, sub_letter, sub_heading,
     sort_order, doctrine_md, distinctions_md, memory_aid,
     key_provisions, key_cases, bar_questions, key_statutes,
     case_cutoff, status, confidence, generated_at, generation_model)
VALUES
    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s)
ON CONFLICT (subject_id, roman_num, COALESCE(sub_letter, ''))
DO UPDATE SET
    topic_heading    = EXCLUDED.topic_heading,
    sub_heading      = EXCLUDED.sub_heading,
    sort_order       = EXCLUDED.sort_order,
    doctrine_md      = EXCLUDED.doctrine_md,
    distinctions_md  = EXCLUDED.distinctions_md,
    memory_aid       = EXCLUDED.memory_aid,
    key_provisions   = EXCLUDED.key_provisions,
    key_cases        = EXCLUDED.key_cases,
    bar_questions    = EXCLUDED.bar_questions,
    key_statutes     = EXCLUDED.key_statutes,
    confidence       = EXCLUDED.confidence,
    generated_at     = NOW(),
    generation_model = EXCLUDED.generation_model,
    status           = EXCLUDED.status
"""


def upsert_topic(conn, record: dict):
    cur = conn.cursor()
    cur.execute(
        UPSERT_SQL,
        (
            str(uuid.uuid4()),
            record["subject_id"],
            record["roman_num"],
            record["topic_heading"],
            record["sub_letter"],
            record["sub_heading"],
            record["sort_order"],
            record["doctrine_md"],
            record["distinctions_md"],
            record["memory_aid"],
            record["key_provisions"],
            record["key_cases"],
            record["bar_questions"],
            record["key_statutes"],
            record["case_cutoff"],
            record["status"],
            record["confidence"],
            record["generation_model"],
        ),
    )
    conn.commit()


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate BAR 2026 reviewer content")
    parser.add_argument("--subject", required=True, choices=list(SUBJECT_MAPS.keys()))
    parser.add_argument("--dry-run", action="store_true",
                        help="Skip AI calls; write placeholder content for schema testing")
    parser.add_argument("--only", metavar="ROMAN",
                        help="Generate only this roman numeral section (e.g. --only I)")
    parser.add_argument("--only-sub", metavar="TOPIC",
                        help="Generate only this specific sub-topic (e.g. --only-sub I.C or --only-sub VIII.F)")
    parser.add_argument("--draft", action="store_true",
                        help="Save as draft instead of publishing automatically")
    parser.add_argument("--case-cutoff", default=DEFAULT_CASE_CUTOFF,
                        metavar="YYYY-MM-DD",
                        help=f"Cutoff date for cases (default: {DEFAULT_CASE_CUTOFF})")
    parser.add_argument("--retry-failed", action="store_true",
                        help="Only regenerate topics listed in logs/failures.json")
    parser.add_argument("--skip-published", action="store_true",
                        help="Skip topics that already have a published record in the DB")
    args = parser.parse_args()

    load_settings()

    case_cutoff = args.case_cutoff
    publish     = not args.draft
    topic_map   = list(SUBJECT_MAPS[args.subject])

    if args.only:
        topic_map = [t for t in topic_map if t["roman_num"] == args.only]
        if not topic_map:
            log.error("No topics found for roman numeral %s", args.only)
            sys.exit(1)

    if args.only_sub:
        # Accept formats: "I.C", "VIII.F", "XII" (no sub-letter)
        raw = args.only_sub.strip().upper()
        if "." in raw:
            parts = raw.split(".", 1)
            filter_roman, filter_sub = parts[0], parts[1]
        else:
            filter_roman, filter_sub = raw, None
        topic_map = [
            t for t in topic_map
            if t["roman_num"] == filter_roman
            and (filter_sub is None or (t.get("sub_letter") or "").upper() == filter_sub)
        ]
        if not topic_map:
            log.error("No topic found for --only-sub %s", args.only_sub)
            sys.exit(1)

    # --retry-failed: load failures.json and filter topic_map
    failures_path = API_DIR / "logs" / "failures.json"
    if args.retry_failed:
        if not failures_path.exists():
            log.error("--retry-failed: logs/failures.json not found")
            sys.exit(1)
        with open(failures_path) as f:
            failures_data = json.load(f)
        failed_keys = {
            (e["subject_id"], e["roman_num"], e.get("sub_letter"))
            for e in failures_data
            if e.get("subject_id") == args.subject
        }
        topic_map = [
            t for t in topic_map
            if (args.subject, t["roman_num"], t.get("sub_letter")) in failed_keys
        ]
        log.info("--retry-failed: %d topics to retry", len(topic_map))
        if not topic_map:
            log.info("Nothing to retry for %s", args.subject)
            sys.exit(0)

    log.info(
        "Subject: %s | Topics: %d | Model: %s | Cutoff: %s | Publish: %s | Dry-run: %s",
        args.subject.upper(), len(topic_map), BAR_MODEL,
        case_cutoff, publish, args.dry_run,
    )

    conn        = get_conn()

    # --skip-published: remove topics that already have a published record in the DB
    if args.skip_published:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT roman_num, COALESCE(sub_letter, '') AS sub_letter
            FROM bar_reviewer_topics
            WHERE subject_id = %s AND status = 'published'
            """,
            (args.subject,),
        )
        already_published = {(row[0], row[1]) for row in cur.fetchall()}
        cur.close()
        before = len(topic_map)
        topic_map = [
            t for t in topic_map
            if (t["roman_num"], t.get("sub_letter") or "") not in already_published
        ]
        skipped = before - len(topic_map)
        log.info("--skip-published: skipping %d already-published topics, %d remaining", skipped, len(topic_map))
        if not topic_map:
            log.info("All topics already published for %s", args.subject)
            conn.close()
            sys.exit(0)
    success     = 0
    failed      = 0
    failure_log = []

    for topic in topic_map:
        conn = _ensure_conn(conn)

        try:
            record = generate_topic(
                conn, topic, args.subject, case_cutoff,
                dry_run=args.dry_run, publish=publish,
            )
            # Reconnect if the connection died during the long AI calls above
            conn = _ensure_conn(conn)
            upsert_topic(conn, record)
            status_word = "Published" if publish else "Saved (draft)"
            log.info("  %s: %s.%s", status_word, topic["roman_num"], topic.get("sub_letter", ""))
            success += 1
        except Exception as e:
            log.error(
                "  FAILED %s.%s: %s",
                topic["roman_num"], topic.get("sub_letter", ""), e,
            )
            log.exception("Full traceback:")
            failed += 1
            failure_log.append({
                "subject_id": args.subject,
                "roman_num":  topic["roman_num"],
                "sub_letter": topic.get("sub_letter"),
                "sub_heading": topic.get("sub_heading") or topic.get("heading", ""),
                "error":      str(e),
                "timestamp":  datetime.utcnow().isoformat(),
            })
            try:
                conn.rollback()
            except Exception:
                pass

        if not args.dry_run:
            time.sleep(_pace)

    conn.close()

    # Write / merge failures.json
    if failure_log:
        failures_path.parent.mkdir(exist_ok=True)
        existing = []
        if failures_path.exists():
            try:
                with open(failures_path) as f:
                    existing = json.load(f)
            except Exception:
                existing = []
        # Remove stale entries for the same subject (replaced by this run's results)
        existing = [
            e for e in existing
            if not (e.get("subject_id") == args.subject
                    and any(
                        t["roman_num"] == e.get("roman_num")
                        and t.get("sub_letter") == e.get("sub_letter")
                        for t in topic_map
                    ))
        ]
        merged = existing + failure_log
        with open(failures_path, "w") as f:
            json.dump(merged, f, indent=2, ensure_ascii=False)
        log.warning("  %d failure(s) written to logs/failures.json", len(failure_log))

    log.info("=" * 60)
    log.info(
        "Done. Published: %d | Failed: %d | Status: %s",
        success, failed, "published" if publish else "draft",
    )


if __name__ == "__main__":
    main()
