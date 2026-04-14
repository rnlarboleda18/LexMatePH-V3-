"""
Ingest structured RCC markdown (same heading patterns as CIV_structured.md) into rcc_codal.

Expects:
  ## BOOK I …
  ## TITLE I …
  ## CHAPTER 1 …
  ### Section N. …

Prerequisite: run scripts/apply_rcc_codal_schema.sql (or apply_rcc_codal_schema.py).
Optionally normalize layout: python LexCode/pipelines/rcc/normalize_codal_md_layout.py …
"""
from __future__ import annotations

import argparse
import json
import os
import re
import uuid
from pathlib import Path

import psycopg2

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_MD = _REPO_ROOT / "LexCode" / "Codals" / "md" / "RCC_structured.md"


def _load_db_url() -> str:
    s = (os.environ.get("DB_CONNECTION_STRING") or "").strip()
    if s:
        return s
    try:
        with open(_REPO_ROOT / "local.settings.json", encoding="utf-8") as f:
            vals = json.load(f).get("Values", {})
        return (vals.get("DB_CONNECTION_STRING") or "").strip()
    except OSError:
        return ""


def parse_roman_to_int(roman: str | None) -> int | None:
    if not roman:
        return None
    roman = roman.strip().upper().rstrip(".")
    roman_map = {
        "I": 1,
        "II": 2,
        "III": 3,
        "IV": 4,
        "V": 5,
        "VI": 6,
        "VII": 7,
        "VIII": 8,
        "IX": 9,
        "X": 10,
        "XI": 11,
        "XII": 12,
        "XIII": 13,
        "XIV": 14,
        "XV": 15,
        "XVI": 16,
        "XVII": 17,
        "XVIII": 18,
        "XIX": 19,
        "XX": 20,
    }
    if roman in roman_map:
        return roman_map[roman]
    try:
        return int(roman)
    except ValueError:
        return None


def ingest_rcc(md_path: Path, *, clear: bool, dry_run: bool) -> int:
    print(f"Reading {md_path}...")
    lines = md_path.read_text(encoding="utf-8").splitlines(keepends=True)

    if dry_run:
        print("[dry-run] No database connection.")
        conn = None
        cur = None
    else:
        url = _load_db_url()
        if not url:
            raise SystemExit("DB_CONNECTION_STRING not set.")
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        if clear:
            cur.execute("DELETE FROM rcc_codal")
            print("Cleared rcc_codal.")

    TABLE_NAME = "rcc_codal"
    context: dict = {
        "book_num": None,
        "book_label": None,
        "title_num": None,
        "title_label": None,
        "chapter_num": None,
        "chapter_label": None,
    }
    current_article: dict = {
        "num": None,
        "title": None,
        "body": [],
        "context": {},
    }
    inserted_count = 0

    pat_book = re.compile(r"^##\s+BOOK\s+([IVXLCDM]+|ONE|TWO)\s+(.*)", re.IGNORECASE)
    pat_title = re.compile(
        r"^##\s+(TITLE|PRELIMINARY TITLE)\s*([IVXLCDM0-9]*)\s*(.*)", re.IGNORECASE
    )
    pat_chapter = re.compile(r"^##\s+CHAPTER\s+([0-9IVX]+)\s+(.*)", re.IGNORECASE)
    pat_article = re.compile(
        r"^###\s+(?:Article|Section)\s+([0-9A-Za-z\-]+)\.\s*(.*)", re.IGNORECASE
    )

    def flush_current_article() -> int:
        if current_article["num"] is None:
            return 0
        final_body = "".join(current_article["body"]).strip()
        ctx = current_article["context"]
        article_title = current_article["title"] or ""
        if dry_run:
            return 1
        assert cur is not None
        cur.execute(
            f"""
            INSERT INTO {TABLE_NAME} (
                id,
                article_num,
                article_title,
                content_md,
                book, book_label,
                title_num, title_label,
                chapter_num, chapter_label,
                created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s,
                %s, %s,
                %s, %s,
                NOW(), NOW()
            )
            """,
            (
                str(uuid.uuid4()),
                current_article["num"],
                article_title,
                final_body,
                ctx.get("book_num"),
                ctx.get("book_label"),
                ctx.get("title_num"),
                ctx.get("title_label"),
                ctx.get("chapter_num"),
                ctx.get("chapter_label"),
            ),
        )
        return 1

    try:
        for original_line in lines:
            line = original_line.strip()

            match = pat_book.match(line)
            if match:
                inserted_count += flush_current_article()
                current_article["num"] = None
                rom = match.group(1)
                lbl = match.group(2).strip()
                context["book_num"] = parse_roman_to_int(rom)
                context["book_label"] = lbl
                context["title_num"] = None
                context["title_label"] = None
                context["chapter_num"] = None
                context["chapter_label"] = None
                continue

            match = pat_title.match(line)
            if match:
                inserted_count += flush_current_article()
                current_article["num"] = None
                type_str = match.group(1).upper()
                if "PRELIMINARY" in type_str:
                    context["title_num"] = 0
                    context["title_label"] = "PRELIMINARY TITLE"
                else:
                    rom = match.group(2)
                    lbl = match.group(3).strip()
                    context["title_num"] = parse_roman_to_int(rom)
                    context["title_label"] = lbl
                context["chapter_num"] = None
                context["chapter_label"] = None
                continue

            match = pat_chapter.match(line)
            if match:
                inserted_count += flush_current_article()
                current_article["num"] = None
                num_str = match.group(1)
                lbl = match.group(2).strip()
                context["chapter_num"] = parse_roman_to_int(num_str)
                context["chapter_label"] = lbl
                continue

            match = pat_article.match(line)
            if match:
                inserted_count += flush_current_article()
                current_article["num"] = match.group(1)
                body_start = match.group(2).strip()
                current_article["title"] = ""
                current_article["body"] = [body_start + "\n" if body_start else ""]
                current_article["context"] = context.copy()
                continue

            if current_article["num"] is not None:
                current_article["body"].append(original_line)

        inserted_count += flush_current_article()

        if not dry_run:
            assert conn is not None
            conn.commit()
        print(f"Successfully processed {inserted_count} articles -> {TABLE_NAME}.")
    except Exception:
        if conn and not dry_run:
            conn.rollback()
        raise
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

    return inserted_count


def main() -> None:
    p = argparse.ArgumentParser(description="Ingest RCC_structured.md into rcc_codal")
    p.add_argument(
        "--md",
        type=Path,
        default=_DEFAULT_MD,
        help=f"Markdown path (default: {_DEFAULT_MD})",
    )
    p.add_argument(
        "--clear",
        action="store_true",
        help="DELETE all rows from rcc_codal before ingest",
    )
    p.add_argument("--dry-run", action="store_true", help="Parse only; no DB writes")
    args = p.parse_args()
    ingest_rcc(args.md.resolve(), clear=args.clear, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
