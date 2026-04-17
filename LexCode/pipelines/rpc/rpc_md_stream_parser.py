"""
Parse LexMate structured RPC.md with full header hierarchy:

  # BOOK …  →  book + book_label + book_rubric (all-caps / rubric lines until ##)
  ## TITLE … / ## PRELIMINARY TITLE  →  title_num + title_label + title_rubric
  ### CHAPTER …  →  chapter heading + chapter_rubric
  #### SECTION …  →  section_num + section_label (run-in label + continuation lines)
  ##### Article …  →  article body

Rubric lines are non-header prose between a structural header and the next deeper
header (or article), e.g. the Book rubric after `# BOOK ONE`, Title rubric after
`## TITLE ONE`, Chapter rubric after `### CHAPTER ONE`.

Used by LexCode/scripts/ingest_rpc_base_from_md.py; keep in sync with
LexCode/pipelines/rpc/3_ingest_codal_reference.py when that script is run for updates.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

Depth = Literal["book", "title", "chapter", "section"]


def parse_roman_to_int(roman: str) -> int | None:
    roman_map = {
        "ONE": 1,
        "TWO": 2,
        "THREE": 3,
        "FOUR": 4,
        "FIVE": 5,
        "SIX": 6,
        "SEVEN": 7,
        "EIGHT": 8,
        "NINE": 9,
        "TEN": 10,
        "ELEVEN": 11,
        "TWELVE": 12,
        "THIRTEEN": 13,
        "FOURTEEN": 14,
        "FIFTEEN": 15,
        "SIXTEEN": 16,
        "SEVENTEEN": 17,
        "EIGHTEEN": 18,
        "NINETEEN": 19,
        "TWENTY": 20,
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
    clean = roman.strip().upper().replace(".", "")
    return roman_map.get(clean)


def _book_num_from_token(raw: str) -> int | None:
    t = raw.strip().upper()
    if not t:
        return None
    first = t.split()[0] if t.split() else t
    book_map = {"ONE": 1, "TWO": 2, "THREE": 3, "IV": 4, "V": 5}
    if first in book_map:
        return book_map[first]
    return parse_roman_to_int(first)


def _merge_rubric(base: str | None, rubric: str | None) -> str | None:
    b = (base or "").strip()
    r = (rubric or "").strip()
    if b and r:
        return f"{b}\n{r}"
    return b or r or None


@dataclass
class RpcArticleRecord:
    article_num: str
    article_title: str
    content_md: str
    book: int | None
    title_num: int | None
    title_label: str | None
    chapter: str | None
    section_num: int | None
    section_label: str | None
    book_label: str | None
    version_markdown: str
    book_rubric: str | None = None
    title_rubric: str | None = None
    chapter_rubric: str | None = None

    def book_label_merged(self) -> str | None:
        return _merge_rubric(self.book_label, self.book_rubric)

    def title_label_merged(self) -> str | None:
        return _merge_rubric(self.title_label, self.title_rubric)

    def chapter_merged(self) -> str | None:
        return _merge_rubric(self.chapter, self.chapter_rubric)


def parse_rpc_codex_md_lines(lines: list[str]) -> list[RpcArticleRecord]:
    context: dict[str, Any] = {
        "book": None,
        "book_label": None,
        "book_rubric": None,
        "title": None,
        "title_num": None,
        "title_rubric": None,
        "chapter": None,
        "chapter_rubric": None,
        "section_num": None,
        "section_label": None,
        "depth": None,
    }

    current: dict[str, Any] = {
        "num": None,
        "title": None,
        "body": [],
        "context": {},
    }

    pat_book = re.compile(r"^#\s+BOOK\s+(.+)$", re.IGNORECASE)
    pat_title = re.compile(
        r"^##\s+(TITLE\s+.+|PRELIMINARY\s+TITLE.*)$",
        re.IGNORECASE,
    )
    pat_chapter = re.compile(r"^###\s+CHAPTER\s+(.+)$", re.IGNORECASE)
    pat_section = re.compile(r"^####\s+SECTION\s+(.+)$", re.IGNORECASE)
    pat_article = re.compile(
        r"^#####\s+Article\s+(\d+)(-[A-Za-z]+)?\.\s*(.*)$",
        re.IGNORECASE,
    )
    pat_md_header = re.compile(r"^#{1,6}\s")

    out: list[RpcArticleRecord] = []

    def _append_rubric(key: str, text: str) -> None:
        prev = context.get(key)
        t = text.strip()
        if not t:
            return
        if prev:
            context[key] = f"{prev}\n{t}"
        else:
            context[key] = t

    def flush_current() -> None:
        if current["num"] is None:
            return
        body = "".join(current["body"]).strip()
        ctx = current["context"]
        num = str(current["num"])
        title = (current["title"] or "").strip()
        book = ctx.get("book")
        title_label = ctx.get("title")
        title_num = ctx.get("title_num")
        chapter = ctx.get("chapter")
        section_num = ctx.get("section_num")
        section_label = ctx.get("section_label")
        book_label = ctx.get("book_label")
        book_rubric = ctx.get("book_rubric")
        title_rubric = ctx.get("title_rubric")
        chapter_rubric = ctx.get("chapter_rubric")

        clean_title = title.rstrip(".")
        if clean_title:
            md_header = f"**Article {num}. {clean_title}.**"
            version_md = f"{md_header} - {body}" if body else md_header
        else:
            md_header = f"**Article {num}.**"
            version_md = f"{md_header} - {body}" if body else md_header

        out.append(
            RpcArticleRecord(
                article_num=num,
                article_title=clean_title or f"Article {num}",
                content_md=body,
                book=book,
                title_num=title_num,
                title_label=title_label,
                chapter=chapter,
                section_num=section_num,
                section_label=section_label,
                book_label=book_label,
                version_markdown=version_md,
                book_rubric=book_rubric,
                title_rubric=title_rubric,
                chapter_rubric=chapter_rubric,
            )
        )

    def handle_floating_non_article(original_line: str) -> None:
        line = original_line.strip()
        if not line or pat_md_header.match(line):
            return
        depth = context.get("depth")
        if depth == "section":
            if context.get("section_label"):
                context["section_label"] = f"{context['section_label']}\n{line}"
            else:
                context["section_label"] = line
        elif depth == "chapter":
            _append_rubric("chapter_rubric", line)
        elif depth == "title":
            _append_rubric("title_rubric", line)
        elif depth == "book":
            _append_rubric("book_rubric", line)

    for original_line in lines:
        line = original_line.strip()

        if match := pat_book.match(line):
            flush_current()
            current = {"num": None, "title": None, "body": [], "context": {}}
            raw_book_line = match.group(1).strip()
            context["book"] = _book_num_from_token(raw_book_line)
            context["book_label"] = raw_book_line.split()[0].upper() if raw_book_line else None
            context["book_rubric"] = None
            context["title"] = None
            context["title_num"] = None
            context["title_rubric"] = None
            context["chapter"] = None
            context["chapter_rubric"] = None
            context["section_num"] = None
            context["section_label"] = None
            context["depth"] = "book"
            continue

        if match := pat_title.match(line):
            flush_current()
            current = {"num": None, "title": None, "body": [], "context": {}}
            raw_title_full = match.group(1).strip()
            context["title"] = raw_title_full
            if "PRELIMINARY" in raw_title_full.upper():
                context["title_num"] = 0
            else:
                raw_num = re.sub(r"^TITLE\s+", "", raw_title_full, flags=re.IGNORECASE).strip()
                context["title_num"] = parse_roman_to_int(raw_num)
            context["title_rubric"] = None
            context["chapter"] = None
            context["chapter_rubric"] = None
            context["section_num"] = None
            context["section_label"] = None
            context["depth"] = "title"
            continue

        if match := pat_chapter.match(line):
            flush_current()
            current = {"num": None, "title": None, "body": [], "context": {}}
            context["chapter"] = f"CHAPTER {match.group(1).strip()}"
            context["chapter_rubric"] = None
            context["section_num"] = None
            context["section_label"] = None
            context["depth"] = "chapter"
            continue

        if match := pat_section.match(line):
            flush_current()
            current = {"num": None, "title": None, "body": [], "context": {}}
            raw_section = match.group(1).strip()
            split_match = re.search(
                r"^([A-Z]+|\d+|I+|II+|III+|IV+|V+|VI+|VII+|VIII+|IX+|X+)\s*[\.\-]+\s*(.*)",
                raw_section,
                re.IGNORECASE,
            )
            if split_match:
                num_str = split_match.group(1)
                label_str = (split_match.group(2) or "").strip()
                sn = parse_roman_to_int(num_str)
                if sn is None and num_str.isdigit():
                    sn = int(num_str)
                context["section_num"] = sn
                context["section_label"] = label_str or None
            else:
                context["section_num"] = parse_roman_to_int(raw_section)
                context["section_label"] = None
            context["depth"] = "section"
            continue

        if match := pat_article.match(line):
            flush_current()
            base = match.group(1)
            suf = match.group(2) or ""
            title_rest = (match.group(3) or "").strip()
            current["num"] = f"{base}{suf}"
            current["title"] = title_rest
            current["body"] = []
            current["context"] = context.copy()
            continue

        if current["num"] is not None:
            current["body"].append(original_line)
        else:
            handle_floating_non_article(original_line)

    flush_current()
    return out


def parse_rpc_codex_md(path: Path) -> list[RpcArticleRecord]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    return parse_rpc_codex_md_lines(lines)


def chapter_num_from_chapter_heading(chapter: str | None) -> int | None:
    if not chapter:
        return None
    m = re.match(r"CHAPTER\s+([A-Za-zIVX]+)", chapter.strip(), re.IGNORECASE)
    if not m:
        return None
    return parse_roman_to_int(m.group(1))


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]
    md = root / "LexCode" / "Codals" / "md" / "RPC.md"
    arts = parse_rpc_codex_md(md)
    print(f"Parsed {len(arts)} articles from {md}")
    assert len(arts) >= 360, f"expected full RPC article count, got {len(arts)}"
    a1 = next(a for a in arts if a.article_num == "1")
    assert a1.book_rubric and "GENERAL PROVISIONS" in a1.book_rubric.upper(), a1.book_rubric
    assert a1.title_rubric and "DATE OF EFFECTIVENESS" in a1.title_rubric.upper(), a1.title_rubric
    a3 = next(a for a in arts if a.article_num == "3")
    assert a3.title_rubric and "FELONIES AND CIRCUMSTANCES" in a3.title_rubric.upper(), a3.title_rubric
    assert a3.chapter_rubric and "FELONIES" in a3.chapter_rubric.upper(), a3.chapter_rubric
    a114 = next(a for a in arts if a.article_num == "114")
    assert a114.chapter_rubric and "NATIONAL SECURITY" in a114.chapter_rubric.upper(), a114.chapter_rubric
    print("Hierarchy self-checks OK.")
    print(f"Art 1 book merged sample: {a1.book_label_merged()!r}")
