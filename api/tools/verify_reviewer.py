"""
BAR 2026 Reviewer Content Verifier
====================================
Two-level verification after generation:

  Level 1 — Completeness: every map entry has a published row in bar_reviewer_topics
             with non-empty doctrine_md.

  Level 2 — Coverage: doctrine_md addresses the granular sub-topics listed in the
             detail field.
             - Fast path: keyword match (instant, no AI cost)
             - Thorough path: AI check via Flash for entries that fail keyword match
               or are flagged thin (--ai flag)

Usage:
    python tools/verify_reviewer.py --subject remedial
    python tools/verify_reviewer.py --subject remedial --ai
    python tools/verify_reviewer.py --subject all
    python tools/verify_reviewer.py --subject remedial --only-sub III.F
    python tools/verify_reviewer.py --subject all --ai --out verify_report.json
"""

import os
import sys
import json
import re
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime

API_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(API_DIR))
sys.path.insert(0, str(API_DIR.parent / "scripts"))

from linker_genai_client import get_linker_genai_client, merge_local_settings_into_env
import psycopg2
from psycopg2.extras import RealDictCursor

from tools.bar_criminal_map   import CRIMINAL_MAP
from tools.bar_remedial_map   import REMEDIAL_MAP
from tools.bar_political_map  import POLITICAL_MAP
from tools.bar_civil_map      import CIVIL_MAP
from tools.bar_labor_map      import LABOR_MAP
from tools.bar_commercial_map import COMMERCIAL_MAP

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

SUBJECT_MAPS = {
    "criminal":   CRIMINAL_MAP,
    "remedial":   REMEDIAL_MAP,
    "political":  POLITICAL_MAP,
    "civil":      CIVIL_MAP,
    "labor":      LABOR_MAP,
    "commercial": COMMERCIAL_MAP,
}

AI_MODEL = "gemini-2.5-flash"


# ── DB helpers ─────────────────────────────────────────────────────────────────

def get_conn():
    merge_local_settings_into_env()
    return psycopg2.connect(
        os.environ["DB_CONNECTION_STRING"],
        keepalives=1, keepalives_idle=60,
        keepalives_interval=10, keepalives_count=5,
    )


def fetch_generated(conn, subject: str) -> dict:
    """Return dict of (roman_num, sub_letter) → most recent row per topic."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT DISTINCT ON (roman_num, COALESCE(sub_letter, ''))
               roman_num, sub_letter, doctrine_md, distinctions_md,
               memory_aid, key_cases, bar_questions, confidence,
               generated_at, generation_model, status
        FROM bar_reviewer_topics
        WHERE subject_id = %s
        ORDER BY roman_num, COALESCE(sub_letter, ''), generated_at DESC
    """, (subject,))
    rows = cur.fetchall()
    cur.close()
    return {(r["roman_num"], r["sub_letter"] or ""): dict(r) for r in rows}


# ── Sub-topic extraction ───────────────────────────────────────────────────────

def extract_subtopics(detail: str) -> list[str]:
    """Extract granular sub-topic keywords from a detail string.

    The detail field uses multi-line wrapped text with semicolons as separators.
    Strategy: flatten the whole string first, then split on semicolons.

    Returns a list of short keyword phrases to search for in doctrine_md.
    """
    if not detail:
        return []

    # Step 1: strip the letter-heading FIRST LINE only ("A. Title text")
    # then flatten remaining lines
    lines = detail.splitlines()
    if lines and re.match(r'^\s*[A-Z]\.\s+', lines[0]):
        lines = lines[1:]
    flat = " ".join(line.strip() for line in lines if line.strip())

    # Step 3: split on semicolons
    parts = re.split(r';', flat)

    subtopics = []
    for part in parts:
        part = part.strip()

        # Strip bracketing chars and numbering
        part = re.sub(r'^[\d]+\.\s*', '', part)
        part = re.sub(r'^[a-zA-Z]\.\s+', '', part)
        part = re.sub(r'^\([a-zA-Z]\)\s*', '', part)
        # Remove all square brackets (broken by semicolon splits inside nested lists)
        part = part.replace('[', '').replace(']', '').strip('()., \t')

        # Remove cross-reference tails: "— Rule 14", "— NCC Art. 2", etc.
        part = re.sub(
            r'\s*[-–—]\s*(Rule|Sec\.|Art\.|R\.A|RA\s*\d|NCC|FC|LC|A\.M|CPRA|RPC|ROC)\b.*',
            '', part
        )
        # Remove parenthetical cross-refs "(relate to Rule 3, Sec. 4)"
        part = re.sub(r'\s*\(relate to[^)]*\)', '', part, flags=re.IGNORECASE)
        # Remove citation-style parentheticals "(RA 11232 Secs. 2/4/18)"
        part = re.sub(r'\s*\([A-Z]{2,}[^)]{0,40}\)', '', part)

        part = part.strip('[]()., \t')

        # Keep meaningful phrases: 4–100 chars, not just a Roman numeral section label
        if 4 <= len(part) <= 100 and not re.match(r'^[IVX]+$', part):
            subtopics.append(part)

    return subtopics


def keyword_coverage(doctrine: str, subtopics: list[str]) -> tuple[list[str], list[str]]:
    """Return (covered, missing) lists based on keyword presence in doctrine."""
    doc_lower  = doctrine.lower()
    covered    = []
    missing    = []
    for st in subtopics:
        # Check if any word of 4+ chars from the sub-topic appears in doctrine
        words = [w for w in re.split(r'\W+', st.lower()) if len(w) >= 4]
        if not words:
            covered.append(st)
            continue
        # Need at least 50% of the meaningful words to appear
        hits = sum(1 for w in words if w in doc_lower)
        if hits >= max(1, len(words) // 2):
            covered.append(st)
        else:
            missing.append(st)
    return covered, missing


# ── AI coverage check ──────────────────────────────────────────────────────────

def ai_coverage_check(
    roman: str, sub_letter: str, sub_heading: str,
    detail: str, doctrine: str,
) -> dict:
    """Ask Flash whether the doctrine covers the granular sub-topics.

    Returns: { "covered": [...], "missing": [...], "verdict": "pass"|"thin"|"fail" }
    """
    # Sanitise doctrine — strip null bytes that can cause empty responses
    doctrine_clean = doctrine.replace('\x00', '').strip()

    prompt = f"""You are a Philippine bar review quality checker.

TOPIC: {roman}.{sub_letter} — {sub_heading}

OFFICIAL SYLLABUS COVERAGE REQUIRED (these sub-topics must all be addressed):
{detail}

GENERATED DOCTRINE (length: {len(doctrine_clean)} chars):
{doctrine_clean[:6000]}

TASK:
For each granular sub-topic listed in the OFFICIAL SYLLABUS COVERAGE above, check
whether the generated doctrine adequately addresses it.

Classify:
- "covered": sub-topic is addressed with at least one substantive rule or principle
- "missing": sub-topic is not addressed at all or only mentioned in passing

Return ONLY valid JSON (no markdown):
{{
  "covered": ["sub-topic text", ...],
  "missing": ["sub-topic text", ...],
  "verdict": "pass" | "thin" | "fail",
  "notes": "brief explanation if verdict is not pass"
}}

Verdict scale:
  pass  = all or nearly all sub-topics covered
  thin  = some gaps but majority covered
  fail  = significant gaps (more than 30% of sub-topics missing)
"""
    try:
        from google import genai
        client = get_linker_genai_client()
        cfg = genai.types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,
            max_output_tokens=4096,
        )
        for attempt in range(3):
            try:
                resp = client.models.generate_content(
                    model=AI_MODEL, contents=prompt, config=cfg
                )
                raw = (resp.text or "").strip()
                if raw:
                    return json.loads(raw)
            except Exception as e:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                else:
                    raise
    except Exception as e:
        log.warning("AI coverage check failed for %s.%s: %s", roman, sub_letter, e)
    return {"covered": [], "missing": [], "verdict": "error", "notes": str(e)}


# ── Core verification ──────────────────────────────────────────────────────────

def verify_subject(
    subject: str,
    topic_map: list,
    generated: dict,
    use_ai: bool = False,
    only_sub: str = "",
) -> list[dict]:
    """Return list of result dicts, one per topic."""
    results = []

    for topic in topic_map:
        roman      = topic["roman_num"]
        sub_letter = topic.get("sub_letter") or ""
        key        = f"{roman}.{sub_letter}"
        sub_heading = topic.get("sub_heading", "")
        detail      = topic.get("detail", "")

        # Filter if --only-sub specified
        if only_sub:
            raw = only_sub.strip().upper()
            if "." in raw:
                f_roman, f_sub = raw.split(".", 1)
            else:
                f_roman, f_sub = raw, None
            if roman != f_roman:
                continue
            if f_sub and sub_letter.upper() != f_sub:
                continue

        row = generated.get((roman, sub_letter))

        result = {
            "key":         key,
            "sub_heading": sub_heading[:80],
            "status":      None,
            "db_status":   row["status"] if row else None,
            "confidence":  row["confidence"] if row else None,
            "level1":      None,   # completeness
            "level2_kw":   None,   # keyword coverage
            "level2_ai":   None,   # AI coverage (if --ai)
            "covered":     [],
            "missing":     [],
            "verdict":     None,
            "notes":       "",
        }

        # ── Level 1: Completeness ──────────────────────────────────────────────
        if not row:
            result["level1"]  = "MISSING"
            result["status"]  = "MISSING"
            result["verdict"] = "MISSING"
            results.append(result)
            continue

        doctrine = row.get("doctrine_md") or ""
        if not doctrine or doctrine.startswith("[Generation error"):
            result["level1"]  = "EMPTY"
            result["status"]  = "EMPTY"
            result["verdict"] = "FAIL"
            result["notes"]   = doctrine[:120] if doctrine else "No doctrine_md"
            results.append(result)
            continue

        result["level1"] = "OK"

        # ── Level 2a: Keyword coverage ─────────────────────────────────────────
        subtopics = extract_subtopics(detail)
        if subtopics:
            covered, missing = keyword_coverage(doctrine, subtopics)
            result["level2_kw"] = f"{len(covered)}/{len(subtopics)}"
            result["covered"]   = covered
            result["missing"]   = missing

            kw_ratio = len(covered) / len(subtopics) if subtopics else 1.0

            # ── Level 2b: AI check (if --ai AND ratio < 1.0, or ratio < 0.7) ──
            if (use_ai and kw_ratio < 1.0) or kw_ratio < 0.70:
                log.info("  AI check: %s.%s (%s)", roman, sub_letter, sub_heading[:40])
                ai_result = ai_coverage_check(
                    roman, sub_letter, sub_heading, detail, doctrine
                )
                result["level2_ai"] = ai_result.get("verdict", "error")
                result["verdict"]   = ai_result.get("verdict", "error")
                result["covered"]   = ai_result.get("covered", covered)
                result["missing"]   = ai_result.get("missing", missing)
                result["notes"]     = ai_result.get("notes", "")
                time.sleep(2)   # pace Flash calls
            else:
                # Verdict from keyword ratio
                if kw_ratio >= 0.85:
                    result["verdict"] = "pass"
                elif kw_ratio >= 0.60:
                    result["verdict"] = "thin"
                else:
                    result["verdict"] = "fail"
        else:
            result["level2_kw"] = "N/A"
            result["verdict"]   = "pass"

        result["status"] = (
            "PASS" if result["verdict"] == "pass" else
            "THIN" if result["verdict"] == "thin" else
            "FAIL"
        )

        results.append(result)

    return results


# ── Reporting ──────────────────────────────────────────────────────────────────

def print_report(subject: str, results: list[dict]):
    total   = len(results)
    missing = sum(1 for r in results if r["status"] == "MISSING")
    empty   = sum(1 for r in results if r["status"] == "EMPTY")
    fail    = sum(1 for r in results if r["status"] == "FAIL")
    thin    = sum(1 for r in results if r["status"] == "THIN")
    passed  = sum(1 for r in results if r["status"] == "PASS")

    print(f"\n{'='*65}")
    print(f"SUBJECT: {subject.upper()}  ({total} topics)")
    print(f"  PASS:    {passed:3}  |  THIN:    {thin:3}  |  FAIL:    {fail:3}")
    print(f"  MISSING: {missing:3}  |  EMPTY:   {empty:3}")
    print(f"{'='*65}")

    for r in results:
        status = r["status"]
        if status == "PASS":
            marker = "[PASS]"
        elif status == "THIN":
            marker = "[THIN]"
        elif status == "FAIL":
            marker = "[FAIL]"
        elif status == "MISSING":
            marker = "[MISS]"
        else:
            marker = "[EMPT]"

        print(f"\n  {marker} {r['key']:8} {r['sub_heading']}")
        if r["level2_kw"] and r["level2_kw"] != "N/A":
            print(f"           keyword coverage: {r['level2_kw']}", end="")
            if r["level2_ai"]:
                print(f"  |  AI verdict: {r['level2_ai']}", end="")
            print()
        if r["missing"]:
            for m in r["missing"][:5]:
                print(f"           [gap] {m[:80]}")
            if len(r["missing"]) > 5:
                print(f"           ... and {len(r['missing'])-5} more gaps")
        if r["notes"]:
            print(f"           note: {r['notes'][:120]}")

    print(f"\n{'='*65}")
    overall = "ALL PASS" if (missing + empty + fail + thin) == 0 else (
        "ISSUES FOUND" if (missing + empty + fail) > 0 else "MINOR GAPS"
    )
    print(f"RESULT: {overall}")
    print(f"{'='*65}\n")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Verify BAR 2026 reviewer generation")
    parser.add_argument("--subject", required=True,
                        choices=list(SUBJECT_MAPS.keys()) + ["all"])
    parser.add_argument("--ai",     action="store_true",
                        help="Use AI (Flash) for coverage checks on all topics")
    parser.add_argument("--only-sub", metavar="TOPIC",
                        help="Verify only this sub-topic (e.g. III.F)")
    parser.add_argument("--out", metavar="FILE",
                        help="Save JSON report to this file")
    args = parser.parse_args()

    merge_local_settings_into_env()

    subjects = list(SUBJECT_MAPS.keys()) if args.subject == "all" else [args.subject]

    conn = get_conn()
    all_results = {}

    for subject in subjects:
        topic_map = SUBJECT_MAPS[subject]
        generated = fetch_generated(conn, subject)
        results   = verify_subject(
            subject, topic_map, generated,
            use_ai=args.ai,
            only_sub=getattr(args, 'only_sub', '') or '',
        )
        all_results[subject] = results
        print_report(subject, results)

    conn.close()

    if args.out:
        out_path = Path(args.out)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({
                "generated_at": datetime.utcnow().isoformat(),
                "results": {
                    subj: [
                        {k: v for k, v in r.items() if k not in ("covered",)}
                        for r in rs
                    ]
                    for subj, rs in all_results.items()
                }
            }, f, indent=2, ensure_ascii=False, default=str)
        log.info("Report saved to %s", out_path)


if __name__ == "__main__":
    main()
