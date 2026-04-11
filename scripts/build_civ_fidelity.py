"""
Civil Code (RA 386) fidelity pipeline -- analogous to scripts/build_rpc_fidelity.py for RPC.

Sources (in priority order):
  A. Word document  (LexCode/Codals/Word/Civil Code Base Code.docx) -- cleanest, 2270 arts
  B. Lawphil HTML   (scrape + HTML parser)
  C. Existing structured MD (--from-md-only)

Steps:
  1. Parse source (DOCX or HTML) -> CIV_structured.md
  2. UPDATE civ_codal by article_num with normalized content_md and structural columns

Uses DB_CONNECTION_STRING from api/local.settings.json (cloud DB by default).

Usage (from repo root):
  python scripts/build_civ_fidelity.py --from-docx        # DOCX -> MD -> DB  (RECOMMENDED)
  python scripts/build_civ_fidelity.py --from-md-only     # sync existing MD to DB
  python scripts/build_civ_fidelity.py                    # scrape Lawphil -> MD -> DB
  python scripts/build_civ_fidelity.py --skip-scrape      # use existing HTML -> MD -> DB
  python scripts/build_civ_fidelity.py --dry-run          # parse only, no DB writes
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
_API_DIR = _REPO_ROOT / "api"
if str(_API_DIR) not in sys.path:
    sys.path.insert(0, str(_API_DIR))

from codal_text import normalize_storage_markdown  # noqa: E402

# Paths under repo
WORD_DIR = _REPO_ROOT / "LexCode" / "Codals" / "Word"
DOC_DIR = _REPO_ROOT / "LexCode" / "Codals" / "doc"
MD_DIR = _REPO_ROOT / "LexCode" / "Codals" / "md"
CIV_DOCX_PATH = WORD_DIR / "Civil Code Base Code.docx"
CIV_HTML_PATH = DOC_DIR / "CIV_base.html"
CIV_MD_PATH = MD_DIR / "CIV_structured.md"
LAWPHIL_CIV_URL = "https://lawphil.net/statutes/repacts/ra1949/ra_386_1949.html"


def _load_db_url() -> str:
    # Check repo root first, then api/ subdir
    candidates = [
        _REPO_ROOT / "local.settings.json",
        _API_DIR / "local.settings.json",
    ]
    for p in candidates:
        if not p.is_file():
            continue
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        url = (data.get("Values") or {}).get("DB_CONNECTION_STRING", "")
        if url and "REPLACE_WITH" not in url:
            # Port 6432 (PgBouncer) is no longer active; normalise to 5432
            url = url.replace(":5432/", ":5432/")
            return url
    raise FileNotFoundError(
        "DB_CONNECTION_STRING not found or is a placeholder in local.settings.json"
    )


def _parse_roman_to_int(roman: str) -> int | None:
    if not roman:
        return None
    roman = roman.strip().upper().rstrip(".")
    roman_map = {
        "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5,
        "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10,
        "XI": 11, "XII": 12, "XIII": 13, "XIV": 14, "XV": 15,
        "XVI": 16, "XVII": 17, "XVIII": 18, "XIX": 19, "XX": 20,
    }
    if roman in roman_map:
        return roman_map[roman]
    try:
        return int(roman)
    except ValueError:
        return None


def _merge_split_centered_headers(headers: list[str]) -> list[str]:
    """
    Lawphil often splits BOOK II and its subtitle across two centered <p> blocks.
    Merge so the MD parser sees one ## BOOK II … line.
    """
    headers = [h.replace("\n", " ").strip() for h in headers if h and h.strip()]
    if not headers:
        return []
    out: list[str] = []
    i = 0
    while i < len(headers):
        h = headers[i]
        if re.match(r"^BOOK\s+[IVXLCDM]+\s*$", h, re.I) and i + 1 < len(headers):
            nxt = headers[i + 1]
            if not re.match(r"^(TITLE|CHAPTER|SECTION)\b", nxt, re.I):
                out.append(f"{h} {nxt}")
                i += 2
                continue
        if re.match(r"^TITLE\s+[IVXLCDM0-9]+\s*$", h, re.I) and i + 1 < len(headers):
            nxt = headers[i + 1]
            if re.match(r"^CHAPTER\s+", nxt, re.I):
                pass
            elif re.match(r"^(PRELIMINARY|GENERAL)\s+PROVISIONS$", nxt, re.I):
                pass
            else:
                out.append(f"{h} {nxt}")
                i += 2
                continue
        if re.match(r"^CHAPTER\s+[0-9IVX]+\s*$", h, re.I) and i + 1 < len(headers):
            nxt = headers[i + 1]
            if not re.match(r"^(BOOK|TITLE|CHAPTER|SECTION)\b", nxt, re.I):
                out.append(f"{h} {nxt}")
                i += 2
                continue
        out.append(h)
        i += 1
    return out


def lawphil_html_to_structured_markdown(html_content: str) -> str:
    try:
        from bs4 import BeautifulSoup
    except ImportError as e:
        raise ImportError(
            "beautifulsoup4 is required. Install: pip install beautifulsoup4"
        ) from e

    soup = BeautifulSoup(html_content, "html.parser")
    paragraphs = soup.find_all("p")
    markdown_parts: list[str] = []
    pending_headers: list[str] = []

    for p in paragraphs:
        for br in p.find_all("br"):
            br.replace_with("\n")
        text = p.get_text().strip()
        if not text:
            continue
        align = (p.get("align") or "").lower()
        article_match = re.match(
            r"^Article\s+([0-9A-Za-z\-]+)\.\s*(.*)", text, re.IGNORECASE | re.DOTALL
        )

        if article_match:
            art_num = article_match.group(1)
            art_body = article_match.group(2).strip()
            if pending_headers:
                merged = _merge_split_centered_headers(pending_headers)
                for header in merged:
                    clean_header = header.replace("\n", " ").strip()
                    markdown_parts.append(f"## {clean_header}\n\n")
                pending_headers = []
            markdown_parts.append(f"### Article {art_num}.\n\n{art_body}\n\n")
        elif align == "center":
            pending_headers.append(text)
        elif align == "justify":
            if markdown_parts:
                markdown_parts[-1] = markdown_parts[-1].rstrip()
                markdown_parts[-1] += f"\n\n{text}\n\n"
            else:
                pending_headers.append(text)
        else:
            if text.isupper() and len(text) < 100:
                pending_headers.append(text)
            elif markdown_parts:
                markdown_parts[-1] = markdown_parts[-1].rstrip()
                markdown_parts[-1] += f"\n\n{text}\n\n"

    final_markdown = "".join(markdown_parts)
    final_markdown = re.sub(
        r"(### Article [0-9A-Za-z\-]+\.)[\s\-]*(.+)", r"\1 \2", final_markdown
    )
    return final_markdown


def download_civ_html(url: str, out_path: Path) -> None:
    import requests

    out_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url} ...")
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    out_path.write_text(r.text, encoding="utf-8")
    print(f"Wrote {out_path} ({len(r.text)} chars)")


def parse_structured_md_to_articles(lines: list[str]) -> list[dict[str, Any]]:
    """
    State machine aligned with LexCode/pipelines/civ/3_ingest_codal_reference.py,
    plus SECTION lines and chapter-only headings (e.g. PRELIMINARY PROVISIONS).
    """
    pat_book = re.compile(r"^##\s+BOOK\s+([IVXLCDM]+|ONE|TWO)\s+(.*)", re.IGNORECASE)
    pat_title = re.compile(
        r"^##\s+(TITLE|PRELIMINARY TITLE)\s*([IVXLCDM0-9]*)\s*(.*)", re.IGNORECASE
    )
    pat_chapter = re.compile(r"^##\s+CHAPTER\s+([0-9IVX]+)\s+(.*)", re.IGNORECASE)
    pat_section = re.compile(r"^##\s+SECTION\s+(.+)$", re.IGNORECASE)
    pat_chapter_plain = re.compile(
        r"^##\s+(PRELIMINARY PROVISIONS|GENERAL PROVISIONS)\s*$", re.IGNORECASE
    )
    pat_article = re.compile(r"^###\s+Article\s+([0-9A-Za-z\-]+)\.\s*(.*)", re.IGNORECASE)

    context: dict[str, Any] = {
        "book_num": None,
        "book_label": None,
        "title_num": None,
        "title_label": None,
        "chapter_num": None,
        "chapter_label": None,
        "section_label": None,
    }

    current: dict[str, Any] = {
        "num": None,
        "title": "",
        "body": [],
        "context": {},
    }

    articles: list[dict[str, Any]] = []

    def flush() -> None:
        if current["num"] is None:
            return
        body = "".join(current["body"]).strip()
        articles.append(
            {
                "article_num": str(current["num"]).strip(),
                "article_title": (current["title"] or "").strip() or None,
                "content_md": body,
                "book": context.get("book_num"),
                "book_label": context.get("book_label"),
                "title_num": context.get("title_num"),
                "title_label": context.get("title_label"),
                "chapter_num": context.get("chapter_num"),
                "chapter_label": context.get("chapter_label"),
                "section_label": context.get("section_label"),
            }
        )

    for original_line in lines:
        line = original_line.strip()

        m = pat_book.match(line)
        if m:
            flush()
            current["num"] = None
            rom = m.group(1)
            lbl = m.group(2).strip()
            context["book_num"] = _parse_roman_to_int(rom)
            context["book_label"] = lbl
            context["title_num"] = None
            context["title_label"] = None
            context["chapter_num"] = None
            context["chapter_label"] = None
            context["section_label"] = None
            continue

        m = pat_title.match(line)
        if m:
            flush()
            current["num"] = None
            type_str = m.group(1).upper()
            if "PRELIMINARY" in type_str:
                context["title_num"] = 0
                context["title_label"] = "PRELIMINARY TITLE"
            else:
                rom = m.group(2)
                lbl = m.group(3).strip()
                context["title_num"] = _parse_roman_to_int(rom)
                context["title_label"] = lbl
            context["chapter_num"] = None
            context["chapter_label"] = None
            context["section_label"] = None
            continue

        m = pat_chapter.match(line)
        if m:
            flush()
            current["num"] = None
            num_str = m.group(1)
            lbl = m.group(2).strip()
            context["chapter_num"] = _parse_roman_to_int(num_str)
            context["chapter_label"] = lbl
            context["section_label"] = None
            continue

        m = pat_chapter_plain.match(line)
        if m:
            flush()
            current["num"] = None
            label = m.group(1).strip()
            if context.get("chapter_num") is None:
                context["chapter_num"] = 1
            context["chapter_label"] = label
            context["section_label"] = None
            continue

        m = pat_section.match(line)
        if m:
            flush()
            current["num"] = None
            context["section_label"] = m.group(1).strip()
            continue

        m = pat_article.match(line)
        if m:
            flush()
            current["num"] = m.group(1)
            body_start = m.group(2).strip()
            current["title"] = ""
            current["body"] = [body_start + "\n" if body_start else ""]
            current["context"] = {k: v for k, v in context.items()}
            continue

        if current["num"] is not None:
            current["body"].append(original_line)

    flush()
    return articles


def _civ_updatable_columns(cur) -> set[str]:
    cur.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'civ_codal'
        """
    )
    return {r[0] for r in cur.fetchall()}


def sync_civ_codal(
    records: list[dict[str, Any]],
    dry_run: bool,
) -> tuple[int, int, list[str]]:
    import psycopg2
    from psycopg2.extras import execute_batch

    if dry_run:
        print(f"[dry-run] Skipping DB; {len(records)} article rows parsed from markdown.")
        return 0, 0, []

    conn = psycopg2.connect(_load_db_url())
    cur = conn.cursor()

    # Discover columns in one query up front
    cols = _civ_updatable_columns(cur)
    want = [
        "article_title",
        "content_md",
        "book",
        "book_label",
        "title_num",
        "title_label",
        "chapter_num",
        "chapter_label",
    ]
    if "section_label" in cols:
        want.append("section_label")

    # Fetch all existing article_nums in one round-trip — no per-row existence checks
    cur.execute("SELECT TRIM(article_num::text) FROM civ_codal")
    existing_keys: set[str] = {r[0] for r in cur.fetchall()}

    set_parts = [f"{c} = %s" for c in want]
    sql = f"""
        UPDATE civ_codal SET
            {", ".join(set_parts)},
            updated_at = NOW()
        WHERE TRIM(article_num::text) = %s
    """

    batch: list[tuple] = []
    warnings: list[str] = []
    for rec in records:
        key = str(rec["article_num"]).strip()
        if key not in existing_keys:
            warnings.append(f"No civ_codal row for article_num={key!r} - skipped")
            continue
        body = normalize_storage_markdown(rec.get("content_md") or "")
        title = (rec.get("article_title") or "") or ""
        vals: list[Any] = [
            title or None,
            body,
            rec.get("book"),
            rec.get("book_label"),
            rec.get("title_num"),
            rec.get("title_label"),
            rec.get("chapter_num"),
            rec.get("chapter_label"),
        ]
        if "section_label" in cols:
            vals.append(rec.get("section_label"))
        vals.append(key)
        batch.append(tuple(vals))

    if not batch:
        cur.close()
        conn.close()
        return 0, len(warnings), warnings

    # Single batch UPDATE — minimal round-trips
    execute_batch(cur, sql, batch, page_size=500)
    conn.commit()
    n = len(batch)
    cur.close()
    conn.close()
    return n, len(warnings), warnings


def main() -> None:
    parser = argparse.ArgumentParser(description="Civil Code base reingest -> civ_codal")
    parser.add_argument("--skip-scrape", action="store_true", help="Do not download HTML (HTML mode only)")
    parser.add_argument(
        "--md",
        type=str,
        default=None,
        help="Structured markdown output path (default: LexCode/Codals/md/CIV_structured.md)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Parse only; no DB updates")
    parser.add_argument(
        "--from-docx",
        action="store_true",
        help="Convert Word doc (LexCode/Codals/Word/Civil Code Base Code.docx) -> MD -> DB (recommended)",
    )
    parser.add_argument(
        "--from-md-only",
        action="store_true",
        help="Skip source parsing; read existing structured markdown and UPDATE civ_codal only",
    )
    args = parser.parse_args()

    md_path = Path(args.md) if args.md else CIV_MD_PATH
    if not md_path.is_absolute():
        md_path = _REPO_ROOT / md_path

    if args.from_md_only:
        if not md_path.is_file():
            print(f"Missing markdown file: {md_path}")
            sys.exit(1)
        md_out = md_path

    elif args.from_docx:
        # --- DOCX path (recommended, cleanest source) ---
        if not CIV_DOCX_PATH.is_file():
            print(f"Missing DOCX: {CIV_DOCX_PATH}")
            sys.exit(1)
        if str(_SCRIPT_DIR) not in sys.path:
            sys.path.insert(0, str(_SCRIPT_DIR))
        from civ_docx_structured import docx_to_structured_markdown, count_articles_in_markdown
        print(f"Converting DOCX -> structured markdown ...")
        structured = docx_to_structured_markdown(CIV_DOCX_PATH)
        ac = count_articles_in_markdown(structured)
        hc = len(re.findall(r"^## ", structured, re.MULTILINE))
        print(f"Parsed: {ac} articles, {hc} ## headers")
        MD_DIR.mkdir(parents=True, exist_ok=True)
        md_out = md_path
        md_out.write_text(structured, encoding="utf-8")
        print(f"Wrote {md_out}")

    else:
        # --- HTML path ---
        if not args.skip_scrape:
            DOC_DIR.mkdir(parents=True, exist_ok=True)
            download_civ_html(LAWPHIL_CIV_URL, CIV_HTML_PATH)
        elif not CIV_HTML_PATH.is_file():
            print(f"Missing {CIV_HTML_PATH}; run without --skip-scrape, or use --from-docx.")
            sys.exit(1)
        html_text = CIV_HTML_PATH.read_text(encoding="utf-8")
        print("Parsing HTML -> structured markdown ...")
        structured = lawphil_html_to_structured_markdown(html_text)
        MD_DIR.mkdir(parents=True, exist_ok=True)
        md_out = md_path
        md_out.write_text(structured, encoding="utf-8")
        ac = len(re.findall(r"^### Article", structured, re.MULTILINE))
        hc = len(re.findall(r"^## ", structured, re.MULTILINE))
        print(f"Wrote {md_out} - {ac} articles, {hc} ## headers")

    lines = md_out.read_text(encoding="utf-8").splitlines(keepends=True)
    records = parse_structured_md_to_articles(lines)
    print(f"Parsed {len(records)} article records from markdown.")

    updated, missing, warns = sync_civ_codal(records, dry_run=args.dry_run)
    if args.dry_run:
        print("[dry-run] No rows written to civ_codal.")
    else:
        print(f"Updated rows: {updated}")
        if missing:
            print(f"Skipped (no DB row for article_num): {missing}")
    for w in warns[:30]:
        print("  WARN:", w)
    if len(warns) > 30:
        print(f"  ... {len(warns) - 30} more warnings")


if __name__ == "__main__":
    main()
