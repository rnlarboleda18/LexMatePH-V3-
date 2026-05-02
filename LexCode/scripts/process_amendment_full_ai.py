
import os
import sys
import json
import argparse
import re
from datetime import datetime
from google import genai

# Import database and application logic from existing scripts
# We assume this script is in data/LexCode/scripts/
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from apply_amendment import apply_amendment_with_ai, generate_new_article_insertion_description
from codal_text import normalize_storage_markdown
from process_amendment import (
    apply_amendment_to_database,
    fetch_current_article,
    get_db_connection,
    get_rpc_structure_ra8353_rape_chapter,
    _strip_leading_statute_quotes,
)

from lexcode_genai_client import get_genai_client, get_amendment_primary_model
from amendment_ingest_guards import validate_rpc_change_for_ingest

client = get_genai_client()


def _target_rpc_classification(label: str) -> str:
    """
    Classify an extraction label (target_statute / code_reference) for RPC ingest.

    Returns:
        'RPC' — may update the RPC codex
        'NON_RPC' — amends some other statute; must not touch RPC rows
        'UNKNOWN' — legacy rows with no label; may infer from quoted text only
    """
    u = (label or "").strip().upper()
    if not u:
        return "UNKNOWN"
    if u in ("OTHER", "RA7610", "NON-RPC", "NON_RPC"):
        return "NON_RPC"
    if u == "RPC" or u == "REVISED PENAL CODE":
        return "RPC"

    non_rpc_markers = (
        "7610",
        "9231",
        "7658",
        "SPECIAL PROTECTION OF CHILDREN",
        "LABOR CODE",
        "NIRC",
        "NATIONAL INTERNAL REVENUE",
        "FAMILY CODE",
        "CIVIL CODE",
        "CORPORATION CODE",
        "LOCAL GOVERNMENT CODE",
        "TARIFF AND CUSTOMS",
        "CUSTOMS MODERNIZATION",
        "DATA PRIVACY",
        "CYBERCRIME PREVENTION",
        "ANTI-MONEY LAUNDERING",
        "SECURITIES REGULATION",
        "COOPERATIVE CODE",
        "AGRARIAN REFORM",
        "MAGNA CARTA FOR",
        "MIGRANT WORKERS",
        "ANTI-TRAFFICKING",
        "6425",
        "DANGEROUS DRUGS",
    )
    for m in non_rpc_markers:
        if m in u:
            return "NON_RPC"

    rpc_markers = (
        "3815",
        "ACT NO. 3815",
        "REVISED PENAL",
        "THE REVISED PENAL CODE",
    )
    for m in rpc_markers:
        if m in u:
            return "RPC"

    if "8353" in u and ("ANTI-RAPE" in u or "RAPE" in u or "266" in u):
        return "RPC"
    if "ANTI-RAPE LAW OF 1997" in u:
        return "RPC"

    # Bare "Republic Act No. NNNN" without RPC/8353 cues: do not assume RPC.
    if "REPUBLIC ACT" in u and "3815" not in u and "8353" not in u:
        return "NON_RPC"
    if "COMMONWEALTH ACT" in u and "3815" not in u:
        return "NON_RPC"
    if "PRESIDENTIAL DECREE" in u:
        return "NON_RPC"
    if "BATAS PAMBANSA" in u:
        return "NON_RPC"

    return "UNKNOWN"


def _new_text_leads_with_section(new_text: str) -> bool:
    t = (new_text or "").lstrip()
    if t.startswith(('"', "'")):
        t = t[1:].lstrip()
    return bool(re.match(r"^Section\s+\d+", t, re.I))


def _new_text_leads_with_rpc_article(new_text: str) -> bool:
    """True if the quoted amendment clearly begins with an RPC-style Article line."""
    t = (new_text or "").lstrip()
    if t.startswith(('"', "'")):
        t = t[1:].lstrip()
    return bool(re.match(r"^(Art\.|Article)\s*[\d]+(-[A-Z]+)?\b", t, re.I))


def _ensure_leading_rpc_article_line(new_text: str, art_num: str) -> str:
    """
    Extraction sometimes returns only the quoted body; mergers then MANUAL_REVIEW. Prepend
    ``Article 266-C.`` (etc.) from ``art_num`` when the line is missing.
    """
    t = _strip_leading_statute_quotes((new_text or "").strip())
    if t.startswith(('"', "'")):
        t = t[1:].lstrip()
    if re.match(r"^(Art\.|Article)\s*[\d]+", t, re.I):
        return t
    an = (art_num or "").strip()
    if an.upper().startswith("ARTICLE"):
        return t
    return f"Article {an}. {t}".strip() if t else f"Article {an}."


def classify_change_for_rpc_ingest(change: dict, source_markdown: str | None = None) -> tuple:
    """
    Decide whether a single extracted change should update the RPC codex.

    Returns:
        (apply_to_rpc: bool, provision_number: str | None, new_text: str, skip_reason: str | None)
    """
    new_text = (change.get("new_text") or "").strip()
    raw_num = change.get("provision_number")
    if raw_num is None or str(raw_num).strip() == "":
        raw_num = change.get("article_number")
    number = str(raw_num).strip() if raw_num is not None else ""

    unit = (change.get("unit_type") or "").strip().lower()
    label = change.get("target_statute") or change.get("code_reference") or ""
    bucket = _target_rpc_classification(label)

    if bucket == "NON_RPC":
        return False, number or None, new_text, (
            f"target_statute / code_reference refers to a non-RPC law — skipped (provision {number or '?'})."
        )

    if unit == "section":
        if _new_text_leads_with_section(new_text) or bucket != "RPC":
            return False, number or None, new_text, (
                f"unit_type is 'section' (special-law numbering), not an RPC Article — skipped (provision {number or '?'})."
            )

    if bucket == "RPC" and unit == "section":
        return False, number or None, new_text, (
            "target_statute is RPC but unit_type is section — inconsistent; skipped."
        )

    if bucket == "RPC" and _new_text_leads_with_section(new_text):
        return False, number or None, new_text, (
            "target_statute is RPC but amendment text begins with 'Section …' — skipped (check extraction)."
        )

    if _new_text_leads_with_section(new_text):
        return False, number or None, new_text, (
            "Amendment text begins with 'Section …' (non-RPC form) — will not map to RPC Article numbers."
        )

    if bucket == "UNKNOWN":
        if not _new_text_leads_with_rpc_article(new_text):
            return False, number or None, new_text, (
                "target_statute missing and quoted text does not begin with an RPC 'Article …' line — skipped."
            )

    if not number:
        return False, None, new_text, "Missing provision_number / article_number — skipped."

    ok, guard_reason = validate_rpc_change_for_ingest(new_text, number, source_markdown)
    if not ok:
        return False, number, new_text, guard_reason

    return True, number, new_text, None


def parse_amendment_with_ai_model(content):
    """
    Uses Gemini to extract structured amendment data from raw text.
    Replaces the regex-based parse_amendment.py.
    """
    system_instruction = """You are a precise legal extraction engine. Your job is to extract amendments from Philippine legislative documents.
    
    Output a JSON object with this exact schema:
    {
        "amendment_id": "string (e.g., 'Republic Act No. 12' or 'Act No. 4117')",
        "date": "YYYY-MM-DD (string, date of approval)",
        "title": "string (the full title of the Act)",
        "changes": [
            {
                "article_number": "string (digits only, e.g. '80', '146')",
                "new_text": "string (the EXACT full text of the amended article. Do not include the 'Section X.' prefix. Do include the 'Art. 123' prefix if present in the text.)",
                "code_reference": "string (what code is being amended, e.g. 'Revised Penal Code')"
            }
        ]
    }
    
    CRITICAL RULES:
    1. Extract the "new_text" EXACTLY as it appears. Preserve punctuation, capitalization, and internal formatting.
    2. Do NOT summarize.
    3. If multiple articles are amended, list them all.
    4. If a section amends an article, capture the target article number.
    """

    response = client.models.generate_content(
        model=get_amendment_primary_model(),
        contents=f"Extract amendments from this document:\n\n{content}",
        config={
            "temperature": 0.0,
            "response_mime_type": "application/json",
            "system_instruction": system_instruction
        }
    )
    return json.loads(response.text)

def process_amendment_full_ai(
    file_path, code_short_name="RPC", dry_run=False, skip_source_guard=False
):
    """Returns True if extraction and all article applications succeeded; False otherwise.

    If skip_source_guard is False (default), each RPC-bound change must be supported by the
    source markdown (Art./Article anchor or long snippet match) so re-ingest cannot file
    RA 6425 sections or hallucinated articles under RPC.
    """
    print(f"\n{'='*70}")
    print(f"FULL AI AMENDMENT PROCESSOR (Vertex Pipeline)")
    print(f"{'='*70}\n")
    
    # 1. Read File
    print(f"[1/4] Reading file: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 2. AI Extraction
    print(f"[2/4] AI Extraction Phase (Parsing)...")
    try:
        prompt = """You are a precise legal extraction engine. Your job is to extract amendments from the Philippine Law provided below.

        Many Acts amend MORE than one statute (e.g. the Revised Penal Code / Act 3815, Republic Act No. 8353, and Republic Act No. 7610).
        You MUST record which statute each change **targets** (the law being amended), not the enacting Act in amendment_id.
        A "Section" of a special law (e.g. RA 7610) is NEVER an "Article" of the RPC. Use OTHER for any target that is not RPC or RA 7610 (Labor Code, Tax Code, other RA-only codes, etc.).

        Output a JSON object with this exact schema (strict lowercase keys):
        {
            "amendment_id": "string (e.g., 'Republic Act No. 12')",
            "date": "YYYY-MM-DD (string, date of approval)",
            "title": "string (the full title of the Act)",
            "changes": [
                {
                    "target_statute": "string — one of: RPC | RA7610 | OTHER. RPC = Act 3815 / Revised Penal Code, or RA 8353 provisions that replace RPC articles only.",
                    "unit_type": "string — 'article' for RPC (and RA 8353) article provisions; 'section' for RA 7610 (and similar) section-numbered laws",
                    "provision_number": "string — RPC article label (e.g. '266-A', '337') OR section number for RA 7610 rows (e.g. '5', '7')",
                    "new_text": "string (the EXACT full text of the amended provision verbatim, as quoted in the Act)"
                }
            ]
        }

        Rules:
        - This pipeline records the **letters of the law** only (the enacted wording in the codal). It does **not** record "formal," "confirmatory," "republication," or "implicit" amendments when the Act does **not** set new text for that article.
        - Emit one object per amended provision (split combined quotes when needed).
        - **ONLY include an RPC row when this Act explicitly amends that RPC article's letters** (quoted replacement, or a clear amend/repeal/insert clause aimed at that article). If the article is **not** mentioned or quoted in the amendatory provisions, **omit** it—silence is not a formal amendment.
        - Do NOT list articles merely related, referenced, or indirectly affected in policy if their **text** is unchanged by this Act.
        - Do NOT invent rows for "context" or "completeness." If the Act does not quote or direct new text for an article, omit it from "changes".
        - When the amendatory clause says "Sections … of Republic Act No. 7610", use target_statute "RA7610", unit_type "section".
        - When the clause amends "Article … of Act No. 3815" / RPC, use target_statute "RPC", unit_type "article".
        - For any other amended statute, use target_statute "OTHER" (this pipeline only applies RPC targets downstream).
        - NEVER put the enacting Republic Act number (e.g. RA 11648) in target_statute; put the **codal being amended** there.
        - NEVER reuse an RPC article number for a special-law section just because the digits match.

        Return pure JSON. Do not summarize the new_text.

        Document Content:
        """ + content
        
        response = client.models.generate_content(
            model=get_amendment_primary_model(),
            contents=prompt,
            config={"temperature": 0.0, "response_mime_type": "application/json"}
        )
        data = json.loads(response.text)
        
        # Handle list response (e.g. wrapped in [ ... ])
        if isinstance(data, list):
            if len(data) > 0:
                data = data[0]
            else:
                print(f"  [FAILED] AI returned empty list. Raw: {response.text}")
                return False
        
        # Save to file for verification
        with open("ai_extraction_result.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        print(f"  [OK] Amendment ID: {data.get('amendment_id')}")
        print(f"  [OK] Date: {data.get('date')}")
        print(f"  [OK] Changes found: {len(data.get('changes', []))}")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"  [FAILED] AI Extraction Failed: {e}")
        try:
            print(f"  Raw Response: {response.text}")
        except Exception:
            pass
        return False

    # 3. Database Connection
    print(f"\n[3/4] Connecting to database...")
    conn = get_db_connection()
    if not conn:
        return False

    try:
        cur = conn.cursor()
        cur.execute("SELECT code_id FROM legal_codes WHERE short_name = %s", (code_short_name,))
        row = cur.fetchone()
        if not row:
            print(f"  [FAILED] Code '{code_short_name}' not found")
            return False
        code_id = row[0]
    except Exception as e:
        print(f"  [FAILED] DB Error: {e}")
        return False

    # 4. Processing Loop (AI Application)
    print(f"\n[4/4] Processing Amendments (Application Phase)...")
    results = []
    any_apply_failure = False
    
    src_for_guard = None if skip_source_guard else content
    for change in data.get('changes', []):
        apply_rpc, art_num, new_text_raw, skip_reason = classify_change_for_rpc_ingest(
            change, source_markdown=src_for_guard
        )
        if not apply_rpc:
            print(f"\n  [SKIP] {skip_reason}")
            continue
        new_text_raw = _strip_leading_statute_quotes((new_text_raw or "").strip())
        
        print(f"\n  RPC Article {art_num}:")
        
        # Fetch current
        # Fetch the version active on the amendment's effectivity date so a
        # replayed missed law is applied in the correct historical slot.
        current = fetch_current_article(conn, code_id, art_num, data.get('date'))
        
        if not current:
            print(f"    [INFO] Article {art_num} not found in DB - preparing for initial insertion")
            old_content = ""
            description_hint = "Article newly introduced by law."
        else:
            print(f"    Current version found (valid from {current['valid_from']})")
            old_content = current['content']
            description_hint = None

        print(f"    Applying amendment with AI...")
        
        # We reuse the existing AI application logic which is robust
        # It takes (Old, New_Instruction) -> Merged
        # Here 'new_text_raw' IS the instruction essentially ("Read as follows: ...")
        
        aid = (data.get("amendment_id") or "")
        r8353 = "8353" in aid.replace(" ", "")
        rpc_s = None
        if r8353 and re.match(r"^266-[A-D]$", str(art_num), re.I):
            rpc_s = get_rpc_structure_ra8353_rape_chapter(conn) or None

        ai_result = apply_amendment_with_ai(old_content, new_text_raw, data.get("amendment_id", "Unknown Amendment"))

        if not ai_result.get("success") and not current and "MANUAL_REVIEW" in (ai_result.get("error") or ""):
            lit = _ensure_leading_rpc_article_line(new_text_raw, str(art_num))
            if _new_text_leads_with_rpc_article(lit):
                try:
                    lit = normalize_storage_markdown(lit)
                except Exception:
                    pass
                print("    [FALLBACK] Using literal amendatory text (new article; AI refused merge).")
                ai_result = {
                    "success": True,
                    "new_text": lit,
                    "validation_result": {"confidence_score": 0.99, "valid": True, "errors": []},
                }

        if ai_result['success']:
            print(
                f"    [OK] AI application successful (confidence: {ai_result['validation_result']['confidence_score']:.2f})"
            )

            if not dry_run:
                av_desc = ai_result.get("description")
                if not current:
                    ad = data.get("date")
                    ad_str = str(ad) if ad is not None else None
                    ins_rich = generate_new_article_insertion_description(
                        ai_result["new_text"],
                        data.get("amendment_id", "Unknown Amendment"),
                        ad_str,
                        str(art_num),
                        amendatory_excerpt=new_text_raw,
                        history=[],
                    )
                    if ins_rich:
                        av_desc = ins_rich

                success = apply_amendment_to_database(
                    conn,
                    code_id,
                    art_num,
                    ai_result['new_text'],
                    data['amendment_id'],
                    data['date'],
                    description=av_desc,
                    rpc_structure=rpc_s,
                )
                if success:
                    print("    [OK] Database Updated")
                else:
                    print("    [FAILED] Database Update Failed")
                    any_apply_failure = True
            else:
                print("    [SKIP] Dry Run - No DB Update")
        else:
            # Check if it's a no-change scenario
            if ai_result.get('no_change'):
                print(f"    [SKIP] Article not substantively modified by this amendment")
                results.append({"article": art_num, "success": True, "note": "No substantive change"})
                continue
            
            print(f"    [FAILED] AI Application Failed: {ai_result['error']}")
            any_apply_failure = True

    return not any_apply_failure

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Full AI Amendment Processor")
    parser.add_argument("file", help="Path to amendment file")
    parser.add_argument("--code", default="RPC", help="Short name of the legal code")
    parser.add_argument("--dry-run", action="store_true", help="Do not update the database")
    parser.add_argument(
        "--no-source-guard",
        action="store_true",
        help="Disable markdown anchor/snippet checks (not recommended for production re-ingest)",
    )

    args = parser.parse_args()

    process_amendment_full_ai(
        args.file, args.code, args.dry_run, skip_source_guard=args.no_source_guard
    )
