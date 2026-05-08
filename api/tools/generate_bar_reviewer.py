"""
BAR 2026 Reviewer Generation Pipeline
======================================
Generates reviewer content for one subject at a time.
Run from the api/ directory:

    python tools/generate_bar_reviewer.py --subject criminal
    python tools/generate_bar_reviewer.py --subject criminal --dry-run

Case cutoff: June 30, 2025
Case priority: En Banc > Gaerlan > Landmark (NEW DOCTRINE / ABANDONMENT / MODIFICATION)
AI models:
  - Gemini 2.5 Pro  → doctrine synthesis + key distinctions
  - Gemini 3 Flash  → memory aids + case relevance connectors
"""

import os
import sys
import json
import uuid
import time
import logging
import argparse
import psycopg2
from pathlib import Path
from psycopg2.extras import RealDictCursor
from typing import Optional

# ── Path setup ────────────────────────────────────────────────────────────────
API_DIR = Path(__file__).parent.parent
SCRIPTS_DIR = API_DIR.parent / "scripts"
sys.path.insert(0, str(API_DIR))
sys.path.insert(0, str(SCRIPTS_DIR))

from linker_genai_client import get_linker_genai_client, merge_local_settings_into_env
from tools.provision_scraper import retrieve_provision
from tools.bar_criminal_map import CRIMINAL_MAP
from tools.bar_remedial_map import REMEDIAL_MAP
from tools.bar_political_map import POLITICAL_MAP
from tools.bar_civil_map import CIVIL_MAP
from tools.bar_labor_map import LABOR_MAP
from tools.bar_commercial_map import COMMERCIAL_MAP

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

CASE_CUTOFF     = "2025-06-30"
MODEL_DOCTRINE  = os.environ.get("BAR_DOCTRINE_MODEL", "gemini-2.5-flash")
MODEL_FLASH     = os.environ.get("BAR_FLASH_MODEL",    "gemini-2.5-flash")
MAX_CASES       = 5


def _ai_generate(
    prompt: str,
    *,
    model: str,
    response_mime_type: str = "text/plain",
    temperature: float = 0.2,
    max_tokens: int = 8192,
    retries: int = 5,
) -> str:
    """Generate content via Vertex AI with exponential backoff on 429s."""
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
            resp = client.models.generate_content(model=model, contents=prompt, config=cfg)
            return resp.text or ""
        except (ResourceExhausted, ServiceUnavailable) as e:
            if attempt == retries - 1:
                raise
            wait = 30 * (2 ** attempt)   # 30s, 60s, 120s, 240s …
            log.warning("Vertex AI 429/503 (attempt %d/%d), retrying in %ds: %s", attempt + 1, retries, wait, e)
            time.sleep(wait)
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                if attempt == retries - 1:
                    raise
                wait = 30 * (2 ** attempt)
                log.warning("Vertex AI rate limit (attempt %d/%d), retrying in %ds", attempt + 1, retries, wait)
                time.sleep(wait)
            else:
                raise

SUBJECT_MAPS = {
    "criminal":    CRIMINAL_MAP,
    "remedial":    REMEDIAL_MAP,
    "political":   POLITICAL_MAP,
    "civil":       CIVIL_MAP,
    "labor":       LABOR_MAP,
    "commercial":  COMMERCIAL_MAP,
}

# ── DB helpers ─────────────────────────────────────────────────────────────────

def load_settings():
    try:
        with open(API_DIR / "local.settings.json") as f:
            data = json.load(f)
            vals = data.get("Values", {})
            db = (vals.get("DB_CONNECTION_STRING") or "").strip()
            for k, v in vals.items():
                if k not in os.environ:
                    os.environ[k] = v
            if db:
                os.environ["DB_CONNECTION_STRING"] = db
    except Exception:
        pass


def get_conn():
    cs = os.environ.get("DB_CONNECTION_STRING", "")
    if not cs:
        raise RuntimeError("DB_CONNECTION_STRING not set")
    return psycopg2.connect(cs)


# ── DB provision fetchers ──────────────────────────────────────────────────────

def fetch_rpc_article(cur, article_num: str) -> Optional[str]:
    cur.execute(
        """SELECT article_title, content_md FROM rpc_codal
           WHERE article_num = %s LIMIT 1""",
        (article_num,)
    )
    row = cur.fetchone()
    if not row:
        return None
    title = row["article_title"] or f"Article {article_num}"
    return f"**{title}**\n\n{row['content_md'] or ''}"


def fetch_const_section(cur, provision_id: str) -> Optional[str]:
    # consti_codal stores article_num as "III-1" (ROMAN-SECTION) directly
    cur.execute(
        """SELECT section_label, article_label, content_md FROM consti_codal
           WHERE article_num = %s LIMIT 1""",
        (provision_id,)
    )
    row = cur.fetchone()
    if not row:
        return None
    label = row["section_label"] or row["article_label"] or provision_id
    return f"**{label}**\n\n{row['content_md'] or ''}"


def fetch_db_provision(cur, provision: dict) -> Optional[str]:
    """Fetch a provision that is sourced from the DB."""
    statute = provision["statute_id"]
    pid     = provision["provision_id"]
    label   = provision["label"]

    if statute == "RPC":
        text = fetch_rpc_article(cur, pid)
    elif statute == "CONST":
        text = fetch_const_section(cur, pid)
    else:
        return None

    if text:
        return text
    log.warning(f"  DB provision not found: {label}")
    return None


def fetch_db_case_by_gr(cur, gr_number: str) -> Optional[dict]:
    """Fetch a specific case by G.R. number for CASE-source provisions."""
    # gr_number like "GR-240337"
    gr = gr_number.replace("GR-", "G.R. No. ")
    cur.execute(
        """SELECT id, short_title, case_number, date, main_doctrine,
                  digest_significance, significance_category, ponente, division,
                  separate_opinions
           FROM sc_decided_cases
           WHERE case_number ILIKE %s AND date <= %s
           LIMIT 1""",
        (f"%{gr.replace('G.R. No. ', '')}%", CASE_CUTOFF)
    )
    return cur.fetchone()


# ── Case fetcher ───────────────────────────────────────────────────────────────

def fetch_cases_for_topic(cur, subject_id: str, provisions: list) -> list:
    """
    Query sc_decided_cases via codal_case_links for provisions linked to this topic.
    Priority: En Banc > Gaerlan ponente > Landmark > recent.
    Uses subquery to satisfy DISTINCT + ORDER BY constraint in PostgreSQL.
    """
    db_provisions = [p for p in provisions if p.get("source") == "db"
                     and p["statute_id"] in ("RPC", "CONST", "RCC", "CIV", "FC", "ROC", "LABOR")]
    statute_provision_pairs = [(p["statute_id"], p["provision_id"]) for p in db_provisions]

    if not statute_provision_pairs:
        cur.execute(
            """SELECT id, short_title, case_number, date,
                      main_doctrine, digest_significance, significance_category,
                      ponente, division, separate_opinions
               FROM (
                 SELECT DISTINCT ON (c.id)
                        c.id, c.short_title, c.case_number, c.date,
                        c.main_doctrine, c.digest_significance, c.significance_category,
                        c.ponente, c.division, c.separate_opinions,
                        CASE WHEN c.division = 'En Banc' THEN 0 ELSE 1 END        AS p1,
                        CASE WHEN c.ponente ILIKE '%%Gaerlan%%' THEN 0 ELSE 1 END AS p2,
                        CASE WHEN c.significance_category IN
                             ('NEW DOCTRINE','ABANDONMENT','MODIFICATION')
                             THEN 0 ELSE 1 END                                     AS p3
                 FROM sc_decided_cases c
                 WHERE c.subject ILIKE %s
                   AND c.date <= %s
                   AND c.main_doctrine IS NOT NULL
               ) sub
               ORDER BY p1, p2, p3, date DESC
               LIMIT %s""",
            (f"%{subject_id}%", CASE_CUTOFF, MAX_CASES)
        )
        return list(cur.fetchall())

    placeholders = " OR ".join(
        ["(l.statute_id = %s AND l.provision_id = %s)"] * len(statute_provision_pairs)
    )
    params = []
    for stat, prov in statute_provision_pairs:
        params.extend([stat, prov])
    params.extend([CASE_CUTOFF, MAX_CASES])

    cur.execute(
        f"""SELECT id, short_title, case_number, date,
                  main_doctrine, digest_significance, significance_category,
                  ponente, division, separate_opinions, specific_ruling
           FROM (
             SELECT DISTINCT ON (c.id)
                    c.id, c.short_title, c.case_number, c.date,
                    c.main_doctrine, c.digest_significance, c.significance_category,
                    c.ponente, c.division, c.separate_opinions,
                    l.specific_ruling,
                    CASE WHEN c.division = 'En Banc' THEN 0 ELSE 1 END        AS p1,
                    CASE WHEN c.ponente ILIKE '%%Gaerlan%%' THEN 0 ELSE 1 END AS p2,
                    CASE WHEN c.significance_category IN
                         ('NEW DOCTRINE','ABANDONMENT','MODIFICATION')
                         THEN 0 ELSE 1 END                                     AS p3
             FROM sc_decided_cases c
             JOIN codal_case_links l ON l.case_id = c.id
             WHERE ({placeholders})
               AND c.date <= %s
               AND c.main_doctrine IS NOT NULL
           ) sub
           ORDER BY p1, p2, p3, date DESC
           LIMIT %s""",
        params
    )
    return list(cur.fetchall())


# ── Question fetcher ───────────────────────────────────────────────────────────

def fetch_bar_questions(cur, subject_id: str, sub_heading: str) -> list:
    cur.execute(
        """SELECT q.year, q.text, a.text AS answer, a.institution
           FROM questions q
           LEFT JOIN answers a ON a.question_id = q.id
           WHERE q.subject ILIKE %s
             AND (q.sub_topic ILIKE %s OR q.sub_topic IS NULL)
           ORDER BY q.year DESC
           LIMIT 3""",
        (f"%{subject_id.replace('_', ' ')}%", f"%{sub_heading[:30]}%")
    )
    return list(cur.fetchall())


# ── Gemini prompt builders ─────────────────────────────────────────────────────

SUBJECT_LABELS = {
    "criminal":   "Criminal Law (10% of Bar)",
    "remedial":   "Remedial Law, Legal and Judicial Ethics, with Practical Exercises (25% of Bar)",
    "political":  "Political Law and Public International Law (15% of Bar)",
    "civil":      "Civil Law and Land Titles and Deeds (20% of Bar)",
    "labor":      "Labor Law and Social Legislation (10% of Bar)",
    "commercial": "Commercial and Taxation Laws (20% of Bar)",
}


def _topic_display(topic: dict) -> str:
    """Return 'Roman.Sub — sub_heading' for any map format."""
    heading = topic.get("sub_heading") or topic.get("heading") or topic.get("topic_heading", "")
    return f"{topic['roman_num']}.{topic.get('sub_letter') or ''} — {heading}"


def build_doctrine_prompt(topic: dict, provisions_text: list, cases: list, subject_id: str = "criminal") -> str:
    provisions_block = "\n\n---\n\n".join(
        f"[{p['label']}]\n{p.get('text') or p.get('retrieved_text', '[text not retrieved]')}"
        for p in provisions_text
    )
    cases_block = "\n\n".join(
        f"CASE: {c['short_title']} | {c['case_number']} | {c['date']} | {c['division']}\n"
        f"PONENTE: {c['ponente']}\n"
        f"DOCTRINE: {c['main_doctrine']}\n"
        f"SIGNIFICANCE: {c.get('significance_category', 'N/A')}"
        for c in cases
    ) or "No linked cases available for this topic."

    subject_label = SUBJECT_LABELS.get(subject_id, subject_id.title())
    return f"""You are a Senior Bar Review Lecturer and Philippine legal scholar.

TASK: Write a structured reviewer section for the following 2026 Philippine Bar Exam topic.

TOPIC: {_topic_display(topic)}
SUBJECT: {subject_label}
CASE CUTOFF: {CASE_CUTOFF}

━━━ STATUTORY BASIS (use ONLY the following; do not introduce other provisions) ━━━
{provisions_block}

━━━ LINKED CASES (use ONLY the following; do not invent cases) ━━━
{cases_block}

━━━ OUTPUT RULES ━━━
1. doctrine_md: 3–6 paragraphs. State the rule clearly. Cite specific articles by number.
   Where a case defines or applies the rule, name the case.
   CRITICAL: Do NOT introduce any legal principle not found in the materials above.
   If a gap exists, write: "[Topic area] — no source material in database."
2. distinctions_md: 2–4 bullet points. The most exam-tested confusions in this topic.
   Only distinctions supported by the provided statutes or cases.
3. memory_aid: One short mnemonic, acronym, or framework (3–6 words or steps).
   Creative but accurate — grounded in the doctrine above.

RETURN ONLY valid JSON (no markdown fences):
{{
  "doctrine_md": "...",
  "distinctions_md": "...",
  "memory_aid": "..."
}}"""


def build_case_connector_prompt(case: dict, sub_heading: str) -> str:
    return f"""You are a Philippine Bar review assistant.

TASK: Write ONE sentence (max 30 words) explaining why the following case is relevant
to the bar exam topic "{sub_heading}". Base your answer ONLY on the doctrine below.
Do NOT add information not in the doctrine.

CASE: {case['short_title']} ({case['case_number']}, {case['date']})
DOCTRINE: {case['main_doctrine']}

Return ONLY valid JSON: {{"relevance": "..."}}"""


# ── Core generation ────────────────────────────────────────────────────────────

def generate_topic(conn, topic: dict, subject_id: str, dry_run: bool = False) -> dict:
    cur = conn.cursor(cursor_factory=RealDictCursor)
    roman         = topic["roman_num"]
    sub_letter    = topic.get("sub_letter")
    # Support both {topic_heading, sub_heading} and flat {heading} formats
    _heading      = topic.get("heading", "")
    topic_heading = topic.get("topic_heading") or _heading
    sub_heading   = topic.get("sub_heading") or _heading
    provisions    = topic.get("provisions", [])

    log.info(f"\n{'='*60}")
    log.info(f"Topic {roman}.{sub_letter or ''} — {sub_heading}")

    # ── Step 1: Gather provision texts ────────────────────────────────────────
    enriched_provisions = []
    confidence = "db-sourced"

    for prov in provisions:
        source = prov.get("source")

        # ── Legacy format: source = "db" ──────────────────────────────────────
        if source == "db":
            text = fetch_db_provision(cur, prov)
            enriched_provisions.append({**prov, "text": text or "[Not found in DB]"})

        elif source == "db_case":
            pass  # handled in Step 2 cases section

        elif source == "scrape":
            result = retrieve_provision(prov)
            enriched_provisions.append({
                **prov,
                "text": result.get("text") or "[Retrieval failed — see source URL]",
                "retrieved_source_url": result.get("source_url"),
                "retrieved_source_type": result.get("source_type"),
            })
            if result.get("retrieval_status") == "ai_fallback":
                confidence = "search-grounded"

        # ── New format: source = "const" | "rpc" | "roc" | "statute" ─────────
        elif source in ("const", "rpc", "roc", "statute"):
            _prov_for_db = {
                "statute_id":   {"const": "CONST", "rpc": "RPC"}.get(source, prov.get("provision_id", "")),
                "provision_id": prov.get("provision_id", ""),
                "label":        prov.get("label") or prov.get("provision_id", ""),
            }
            if source == "const":
                # provision_id format: "art-3-sec-1" → consti_codal key e.g. "III-1"
                _INT_TO_ROMAN = {1:"I",2:"II",3:"III",4:"IV",5:"V",6:"VI",7:"VII",
                                 8:"VIII",9:"IX",10:"X",11:"XI",12:"XII",13:"XIII",
                                 14:"XIV",15:"XV",16:"XVI",17:"XVII",18:"XVIII"}
                raw_id = prov.get("provision_id", "")
                parts = raw_id.replace("art-", "").split("-sec-")
                if len(parts) == 2:
                    try:
                        art_roman = _INT_TO_ROMAN.get(int(parts[0]), parts[0].upper())
                    except Exception:
                        art_roman = parts[0].upper()
                    _prov_for_db["provision_id"] = f"{art_roman}-{parts[1]}"
                text = fetch_const_section(cur, _prov_for_db["provision_id"])
                enriched_provisions.append({**prov, "label": _prov_for_db["label"], "text": text or "[Not found in DB]"})
            elif source == "rpc":
                text = fetch_rpc_article(cur, prov.get("provision_id", ""))
                enriched_provisions.append({**prov, "text": text or "[Not found in DB]"})
            else:
                # roc / statute — no DB table yet; treat as scrape via lawphil URL if available
                url = prov.get("url") or prov.get("lawphil_url", "")
                if url:
                    result = retrieve_provision({"source": "scrape", "url": url, "label": prov.get("label", "")})
                    enriched_provisions.append({
                        **prov,
                        "text": result.get("text") or "[Retrieval failed]",
                        "retrieved_source_url": url,
                    })
                    if result.get("retrieval_status") == "ai_fallback":
                        confidence = "search-grounded"
                else:
                    enriched_provisions.append({**prov, "text": f"[{source}: {prov.get('provision_id', '')}]"})

        # ── New format: source = "lawphil" — scrape by URL ───────────────────
        elif source == "lawphil":
            url = prov.get("url", "")
            result = retrieve_provision({"source": "scrape", "url": url, "label": prov.get("label", url)})
            enriched_provisions.append({
                **prov,
                "label": prov.get("label") or url,
                "text": result.get("text") or "[Retrieval failed]",
                "retrieved_source_url": url,
            })
            if result.get("retrieval_status") == "ai_fallback":
                confidence = "search-grounded"

        # ── New format: source = "ai" — no provision text; AI synthesises ────
        elif source == "ai":
            note = prov.get("note", "")
            enriched_provisions.append({**prov, "label": note, "text": f"[AI synthesis note: {note}]"})
            confidence = "ai-synthesized"

    # ── Step 2: Fetch cases ────────────────────────────────────────────────────
    cases = fetch_cases_for_topic(cur, subject_id, provisions)
    log.info(f"  Cases found: {len(cases)}")

    # Handle explicit CASE-source provisions (syllabus-cited specific cases)
    for prov in provisions:
        if prov.get("source") == "db_case":
            specific_case = fetch_db_case_by_gr(cur, prov["provision_id"])
            if specific_case and not any(c["id"] == specific_case["id"] for c in cases):
                cases.insert(0, specific_case)
                cases = cases[:MAX_CASES]

    # ── Step 3: Generate case connectors (Flash — fast, high volume) ──────────
    cases_with_relevance = []
    for case in cases:
        if dry_run:
            relevance = "[dry-run]"
        else:
            try:
                raw = _ai_generate(
                    build_case_connector_prompt(case, sub_heading),
                    response_mime_type="application/json",
                    model=MODEL_FLASH,
                )
                relevance = json.loads(raw).get("relevance", "")
            except Exception as e:
                log.warning(f"  Flash connector failed for {case['short_title']}: {e}")
                relevance = ""

        sep_ops = case.get("separate_opinions")
        if isinstance(sep_ops, str):
            try:
                sep_ops = json.loads(sep_ops)
            except Exception:
                sep_ops = []

        cases_with_relevance.append({
            "case_id":              str(case["id"]),
            "gr_number":            case.get("case_number", ""),
            "short_title":          case.get("short_title", ""),
            "date":                 str(case.get("date", "")),
            "ponente":              case.get("ponente", ""),
            "division":             case.get("division", ""),
            "main_doctrine":        case.get("main_doctrine", ""),
            "bar_trap":             case.get("digest_significance", ""),
            "significance_category": case.get("significance_category", ""),
            "relevance_to_topic":   relevance,
            "separate_opinions":    sep_ops or [],
        })
        time.sleep(0.3)

    # ── Step 4: Fetch past bar questions ──────────────────────────────────────
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

    # ── Step 5: Generate doctrine + distinctions (Pro) ────────────────────────
    if dry_run:
        doctrine_md     = "[dry-run doctrine]"
        distinctions_md = "[dry-run distinctions]"
        memory_aid      = "[dry-run mnemonic]"
        model_used      = "dry-run"
    else:
        prompt = build_doctrine_prompt(topic, enriched_provisions, cases, subject_id=subject_id)
        try:
            raw  = _ai_generate(
                prompt,
                response_mime_type="application/json",
                temperature=0.2,
                max_tokens=16384,
                model=MODEL_DOCTRINE,
            )
            data = json.loads(raw)
            doctrine_md     = data.get("doctrine_md", "")
            distinctions_md = data.get("distinctions_md", "")
            memory_aid      = data.get("memory_aid", "")
            model_used      = MODEL_DOCTRINE
        except Exception as e:
            log.error(f"  Pro generation failed: {e}")
            doctrine_md     = f"[Generation error: {e}]"
            distinctions_md = ""
            memory_aid      = ""
            model_used      = MODEL_DOCTRINE
            confidence      = "ai-synthesized"

    # ── Step 6: Build key_provisions payload ──────────────────────────────────
    key_provisions = []
    for p in enriched_provisions:
        key_provisions.append({
            "statute_id":   p.get("statute_id", ""),
            "provision_id": p.get("provision_id", ""),
            "label":        p.get("label") or p.get("note", ""),
            "text":         p.get("text") or p.get("retrieved_text", ""),
            "source_url":   p.get("retrieved_source_url") or p.get("scrape_url") or p.get("url", ""),
            "source_type":  p.get("retrieved_source_type", p.get("source", "")),
        })

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
        "key_provisions":   json.dumps(key_provisions),
        "key_cases":        json.dumps(cases_with_relevance),
        "bar_questions":    json.dumps(bar_questions),
        "case_cutoff":      CASE_CUTOFF,
        "status":           "draft",
        "confidence":       confidence,
        "generated_at":     "NOW()",
        "generation_model": model_used,
    }


# ── Upsert to DB ───────────────────────────────────────────────────────────────

UPSERT_SQL = """
INSERT INTO bar_reviewer_topics
    (id, subject_id, roman_num, topic_heading, sub_letter, sub_heading,
     sort_order, doctrine_md, distinctions_md, memory_aid,
     key_provisions, key_cases, bar_questions,
     case_cutoff, status, confidence, generated_at, generation_model)
VALUES
    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s)
ON CONFLICT (subject_id, roman_num, COALESCE(sub_letter, ''))
DO UPDATE SET
    doctrine_md      = EXCLUDED.doctrine_md,
    distinctions_md  = EXCLUDED.distinctions_md,
    memory_aid       = EXCLUDED.memory_aid,
    key_provisions   = EXCLUDED.key_provisions,
    key_cases        = EXCLUDED.key_cases,
    bar_questions    = EXCLUDED.bar_questions,
    confidence       = EXCLUDED.confidence,
    generated_at     = NOW(),
    generation_model = EXCLUDED.generation_model,
    status           = 'draft'
"""


def upsert_topic(conn, record: dict):
    cur = conn.cursor()
    cur.execute(UPSERT_SQL, (
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
        record["case_cutoff"],
        record["status"],
        record["confidence"],
        record["generation_model"],
    ))
    conn.commit()


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate BAR 2026 reviewer content")
    parser.add_argument("--subject", required=True, choices=list(SUBJECT_MAPS.keys()),
                        help="Subject to generate")
    parser.add_argument("--dry-run", action="store_true",
                        help="Skip AI calls; write placeholder content to DB for schema testing")
    parser.add_argument("--only", metavar="ROMAN",
                        help="Generate only this roman numeral topic (e.g. --only I)")
    args = parser.parse_args()

    load_settings()
    topic_map = SUBJECT_MAPS[args.subject]

    if args.only:
        topic_map = [t for t in topic_map if t["roman_num"] == args.only]
        if not topic_map:
            log.error(f"No topics found for roman numeral {args.only}")
            sys.exit(1)

    log.info(f"Subject: {args.subject.upper()} | Topics: {len(topic_map)} | Dry run: {args.dry_run}")
    conn = get_conn()

    success, failed = 0, 0
    for topic in topic_map:
        try:
            record = generate_topic(conn, topic, args.subject, dry_run=args.dry_run)
            upsert_topic(conn, record)
            log.info(f"  ✓ Saved: {topic['roman_num']}.{topic.get('sub_letter','')}")
            success += 1
            time.sleep(5.0)   # pacing between topics to avoid Vertex AI rate limits
        except Exception as e:
            log.error(f"  ✗ FAILED {topic['roman_num']}.{topic.get('sub_letter','')}: {e}")
            failed += 1
            try:
                conn.rollback()
            except Exception:
                pass

    conn.close()
    log.info(f"\n{'='*60}")
    log.info(f"Done. Success: {success} | Failed: {failed}")
    log.info(f"All records saved with status='draft'. Review in admin panel before publishing.")


if __name__ == "__main__":
    main()
