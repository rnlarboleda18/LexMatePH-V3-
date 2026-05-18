"""
Step 3 — Parse scraped MD files and load into sc_issuances_codal.

Parser handles:
  - Section N. Title. - Body  (most AM rules and statutes)
  - CANON I [Title] + Section N. … (CPRA)
  - CANON 1 / Rule 1.01 (NCJC)
  - PART / CHAPTER / TITLE group headers

Idempotent: deletes existing rows per statute before re-inserting.
Run after 1_scrape_issuances.py and 2_create_schema.py.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path
from typing import Optional

import psycopg2
import psycopg2.extras

_REPO_ROOT = Path(__file__).resolve().parents[3]
MD_DIR     = _REPO_ROOT / "LexCode" / "Codals" / "md" / "remedial"


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


STATUTES = [
    {"statute_id": "AM-07-9-12-SC",  "filename": "am_07_9_12_sc_2007",  "label": "Rule on the Writ of Amparo (A.M. No. 07-9-12-SC)"},
    {"statute_id": "AM-08-1-16-SC",  "filename": "am_08_1_16_sc_2008",  "label": "Rule on the Writ of Habeas Data (A.M. No. 08-1-16-SC)"},
    {"statute_id": "AM-09-6-8-SC",   "filename": "am_09_6_8_sc_2010",   "label": "Rules of Procedure for Environmental Cases — Kalikasan (A.M. No. 09-6-8-SC)"},
    {"statute_id": "AM-01-7-01-SC",  "filename": "am_01_7_01_sc_2001",  "label": "Rules on Electronic Evidence (A.M. No. 01-7-01-SC)"},
    {"statute_id": "CPRA",           "filename": "am_22_09_01_sc_2023", "label": "Code of Professional Responsibility and Accountability (A.M. No. 22-09-01-SC)"},
    {"statute_id": "AM-02-8-13-SC",  "filename": "am_02_8_13_sc_2004",  "label": "2004 Rules on Notarial Practice (A.M. No. 02-8-13-SC)"},
    {"statute_id": "NCJC",           "filename": "am_03_05_01_sc_2004", "label": "New Code of Judicial Conduct for the Philippine Judiciary (A.M. No. 03-05-01-SC)"},
    {"statute_id": "RA-11642",       "filename": "ra_11642_2022",       "label": "Republic Act No. 11642 — Domestic Administrative Adoption and Alternative Child Care Act"},
]

# Group-level structural headers (Canon, Part, Title, Chapter)
_GROUP_RE = re.compile(
    r'^(CANON|PART|TITLE|CHAPTER)\s+([IVXLCDM\d]+)[.\s]*(?:[-–—]\s*)?(.*)$',
    re.IGNORECASE,
)
# Unnumbered group headers (e.g. GENERAL PROVISIONS, LAWYER'S OATH)
_UNNUMBERED_GROUP_RE = re.compile(
    r"^(GENERAL PROVISIONS|TRANSITORY PROVISIONS|PRELIMINARY PROVISIONS|MISCELLANEOUS PROVISIONS|LAWYER'S OATH)$",
    re.IGNORECASE,
)
# Standard section headers: SECTION 1. / Section 1. / SEC. 1.
_SEC_RE = re.compile(
    r'^(?:SECTION|SEC\.?|Section)\s+(\d+[A-Za-z]?)[.:]?\s*(.*)',
    re.IGNORECASE,
)
# Decimal rule headers: Rule 1.01 (NCJC style)
_RULE_RE = re.compile(
    r'^Rule\s+(\d+\.\d+)[.:]?\s*(.*)',
    re.IGNORECASE,
)
# Integer/Roman rule group headers: RULE 1 COVERAGE / RULE I IMPLEMENTATION.
# [IVXLCDM\d]+ matches both Roman numerals (I, II, IV, VI …) and decimal integers.
# IGNORECASE handles all-caps (Notarial Practice, Env Cases) and mixed-case (Electronic Evidence).
# Negative lookahead (?!\.\d) excludes NCJC decimal headers like "Rule 1.01".
_RULE_GROUP_RE = re.compile(r'^Rule\s+([IVXLCDM\d]+)(?!\.\d)\s*(.*)', re.IGNORECASE)


def _split_title_body(rest: str) -> tuple[str, str]:
    """Split 'Title. - Body' into (title, body_start) using dash separators."""
    m = re.match(r'^(.*?)\s*[-–—]\s+(.*)', rest, re.DOTALL)
    if m:
        return m.group(1).rstrip('. ').strip(), m.group(2).strip()
    return rest.rstrip('. ').strip(), ""


def parse_statute_md(text: str, statute_id: str, statute_label: str) -> list[dict]:
    """Convert flat cleaned MD text into structured records."""
    records: list[dict] = []
    sort_order = 0

    cur_group_type:  Optional[str] = None
    cur_group_num:   Optional[str] = None
    cur_group_label: Optional[str] = None
    # Parent-level context (PART/CHAPTER/TITLE) preserved when a RULE sub-group follows.
    cur_part_num:    Optional[str] = None
    cur_part_label:  Optional[str] = None
    cur_sec_num:     Optional[str] = None
    cur_sec_title:   Optional[str] = None
    cur_lines:       list[str]     = []

    def emit() -> None:
        nonlocal sort_order
        if cur_sec_num is None:
            return
        body_parts = [p.strip() for p in "\n".join(cur_lines).split("\n\n") if p.strip()]
        content = "\n\n".join(body_parts)
        if not content:
            return
        records.append({
            "id":            str(uuid.uuid4()),
            "statute_id":    statute_id,
            "statute_label": statute_label,
            "group_type":    cur_group_type,
            "group_num":     cur_group_num,
            "group_label":   cur_group_label,
            "part_num":      cur_part_num,
            "part_label":    cur_part_label,
            "section_num":   cur_sec_num,
            "section_title": cur_sec_title or "",
            "content_md":    content,
            "sort_order":    sort_order,
        })
        sort_order += 1

    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1

        gm = _GROUP_RE.match(line)
        if gm:
            emit()
            gtype = gm.group(1).capitalize()
            gnum  = gm.group(2).strip()
            glbl  = gm.group(3).strip()
            # Peek at next non-blank line for group title if it wasn't inline
            if not glbl and i < len(lines):
                nxt = lines[i].strip()
                if nxt and not _GROUP_RE.match(nxt) and not _RULE_GROUP_RE.match(nxt) and not _SEC_RE.match(nxt) and not _RULE_RE.match(nxt):
                    glbl = nxt
                    i += 1
            if gtype.upper() in ('PART', 'CHAPTER', 'TITLE'):
                # Save as parent context — a RULE header will follow and become the
                # primary group; if sections follow directly (no RULE), the group_type
                # below acts as the primary group and part_num duplicates it (harmless).
                cur_part_num   = gnum
                cur_part_label = glbl
            else:
                # CANON and other top-level groups own sections directly — clear part ctx.
                cur_part_num   = None
                cur_part_label = None
            cur_group_type  = gtype
            cur_group_num   = gnum
            cur_group_label = glbl
            cur_sec_num   = None
            cur_sec_title = None
            cur_lines     = []
            continue

        rgm = _RULE_GROUP_RE.match(line)
        if rgm:
            emit()
            cur_group_type  = 'Rule'
            cur_group_num   = rgm.group(1).strip()
            cur_group_label = rgm.group(2).strip()
            if not cur_group_label and i < len(lines):
                nxt = lines[i].strip()
                if nxt and not _GROUP_RE.match(nxt) and not _RULE_GROUP_RE.match(nxt) and not _SEC_RE.match(nxt) and not _RULE_RE.match(nxt):
                    cur_group_label = nxt
                    i += 1
            cur_sec_num   = None
            cur_sec_title = None
            cur_lines     = []
            continue

        ugm = _UNNUMBERED_GROUP_RE.match(line)
        if ugm:
            emit()
            cur_group_type  = ' '.join(w.capitalize() for w in ugm.group(1).split())
            cur_group_num   = None
            # Space sentinel: truthy so first text line goes into section-0 content, not group_label;
            # codex.py strips it to '' so it doesn't appear in the API response.
            cur_group_label = ' '
            cur_part_num    = None
            cur_part_label  = None
            cur_sec_num     = None
            cur_sec_title   = None
            cur_lines       = []
            continue

        sm = _SEC_RE.match(line) or _RULE_RE.match(line)
        if sm:
            emit()
            cur_sec_num       = sm.group(1)
            title, body_start = _split_title_body(sm.group(2).strip())
            cur_sec_title     = title
            cur_lines         = [body_start] if body_start else []
            continue

        if cur_sec_num is not None and line:
            cur_lines.append(line)
        elif cur_sec_num is not None and not line:
            # Preserve paragraph break within a section — emit a blank sentinel so
            # emit()'s split("\n\n") can recover paragraph boundaries.
            if cur_lines and cur_lines[-1] != "":
                cur_lines.append("")
        elif cur_sec_num is None and cur_group_type is not None and line and not cur_group_label:
            # Text sitting between a group header and the first section (no label yet)
            cur_group_label = line
        elif cur_sec_num is None and cur_group_type is not None and line and cur_group_label:
            # Introductory paragraph between the group label and the first numbered section.
            # Emit as section "0" so it gets its own version_id and can carry jurisprudence links.
            cur_sec_num   = "0"
            cur_sec_title = ""
            cur_lines     = [line]

    emit()
    return records


def ingest_statute(cur, statute: dict) -> int:
    sid     = statute["statute_id"]
    label   = statute["label"]
    md_path = MD_DIR / f"{statute['filename']}.md"

    if not md_path.exists():
        print(f"  [SKIP] MD file not found: {md_path.name} — run 1_scrape_issuances.py first")
        return 0

    text    = md_path.read_text(encoding="utf-8")
    records = parse_statute_md(text, sid, label)

    if not records:
        print(f"  [WARN] No sections parsed from {md_path.name} — check the raw MD format")
        return 0

    cur.execute("DELETE FROM sc_issuances_codal WHERE statute_id = %s", (sid,))

    psycopg2.extras.execute_values(
        cur,
        """INSERT INTO sc_issuances_codal
             (id, statute_id, statute_label, group_type, group_num, group_label,
              part_num, part_label,
              section_num, section_title, content_md, sort_order)
           VALUES %s""",
        [
            (
                r["id"], r["statute_id"], r["statute_label"], r["group_type"],
                r["group_num"], r["group_label"],
                r.get("part_num"), r.get("part_label"),
                r["section_num"], r["section_title"], r["content_md"], r["sort_order"],
            )
            for r in records
        ],
    )
    return len(records)


def main() -> None:
    db_url = _load_db_url()
    if not db_url:
        raise RuntimeError("DB_CONNECTION_STRING not found in env or local.settings.json")

    conn = psycopg2.connect(db_url)
    psycopg2.extras.register_uuid()
    cur  = conn.cursor()

    total = 0
    for statute in STATUTES:
        sid = statute["statute_id"]
        print(f"\n[{sid}]")
        n = ingest_statute(cur, statute)
        print(f"  Inserted {n} rows")
        total += n

    conn.commit()
    cur.close()
    conn.close()
    print(f"\nDone. Total rows inserted: {total}")


if __name__ == "__main__":
    main()
