"""
Convert Civil Code Word (.docx) to the same structured markdown format used by
build_civ_fidelity.parse_structured_md_to_articles (## BOOK/TITLE/CHAPTER/SECTION,
### Article N.).

The base document uses plain paragraphs (no Word heading styles); hierarchy is
inferred from lines that begin BOOK / TITLE / CHAPTER / SECTION / ARTICLE.
Run-in articles (e.g. \"... ARTICLE 965. The direct line...\") are split so every
article becomes its own block (2270 articles).
"""

from __future__ import annotations

import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

_W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _iter_docx_paragraph_texts(docx_path: Path) -> list[str]:
    z = zipfile.ZipFile(docx_path)
    try:
        root = ET.fromstring(z.read("word/document.xml"))
    finally:
        z.close()
    out: list[str] = []
    for p in root.findall(f".//{_W_NS}p"):
        t = "".join(n.text or "" for n in p.findall(f".//{_W_NS}t")).strip()
        if t:
            out.append(t)
    return out


def _expand_run_in_articles(lines: list[str]) -> list[str]:
    """
    Split paragraphs that glue the next article into the prior body, e.g.
    '...(916a) ARTICLE 965. The direct line...'.

    Only split before *uppercase* ARTICLE + number + dot (Word source style), and only
    when preceded by end-of-citation / sentence punctuation so we do not split phrases
    like 'See Article 5' in running text.
    """
    out: list[str] = []
    # Uppercase ARTICLE only; lookbehind is fixed-width: ) or . or ; then optional single space
    split_re = re.compile(r"(?<=[\.\);:])(?= ARTICLE\s+[0-9]{1,4}[A-Za-z\-]*\.\s)")
    for line in lines:
        s = line.strip()
        if not s:
            continue
        # Line-start article: allow split at beginning without lookbehind
        if s.startswith("ARTICLE ") or s.startswith("Article "):
            chunks = [s]
        else:
            chunks = split_re.split(" " + s)
            if chunks and chunks[0].startswith(" "):
                chunks[0] = chunks[0][1:].lstrip()
            chunks = [c for c in chunks if c and c.strip()]
        if len(chunks) <= 1:
            out.append(s)
            continue
        for ch in chunks:
            ch = ch.strip()
            if ch:
                out.append(ch)
    return out


def _merge_structure_subtitles(lines: list[str]) -> list[str]:
    """
    Merge BOOK I + 'Persons', TITLE I + subtitle, CHAPTER 1 + description,
    SECTION 1 + description when the following line is not a structural keyword.
    """
    out: list[str] = []
    i = 0
    struct_next = re.compile(
        r"^(BOOK|TITLE|CHAPTER|SECTION|PRELIMINARY\s+TITLE|ARTICLE)\b",
        re.IGNORECASE,
    )
    while i < len(lines):
        t = lines[i].strip()
        if not t:
            i += 1
            continue

        merged = False
        if i + 1 < len(lines):
            nxt = lines[i + 1].strip()
            if nxt and not struct_next.match(nxt):
                if re.match(r"^BOOK\s+[IVXLCDM]+\s*$", t, re.I):
                    out.append(f"{t} {nxt}")
                    i += 2
                    merged = True
                elif re.match(r"^TITLE\s+[IVXLCDM0-9]+\s*$", t, re.I):
                    out.append(f"{t} {nxt}")
                    i += 2
                    merged = True
                elif re.match(r"^CHAPTER\s+[0-9IVX]+\s*$", t, re.I):
                    out.append(f"{t} {nxt}")
                    i += 2
                    merged = True
                elif re.match(r"^SECTION\s+\d+\s*$", t, re.I):
                    out.append(f"{t} {nxt}")
                    i += 2
                    merged = True
        if not merged:
            out.append(t)
            i += 1
    return out


def _lines_to_structured_markdown(lines: list[str]) -> str:
    parts: list[str] = []
    for raw in lines:
        u = raw.strip()
        if not u:
            continue
        ul = u.upper()
        if ul.startswith("PRELIMINARY TITLE"):
            parts.append(f"## {u}\n\n")
        elif re.match(r"^BOOK\s+", u, re.I):
            parts.append(f"## {u}\n\n")
        elif re.match(r"^TITLE\s+", u, re.I):
            parts.append(f"## {u}\n\n")
        elif re.match(r"^CHAPTER\s+", u, re.I):
            parts.append(f"## {u}\n\n")
        elif re.match(r"^SECTION\s+", u, re.I):
            parts.append(f"## {u}\n\n")
        elif re.match(r"^ARTICLE\s+", u, re.I):
            m = re.match(r"^(ARTICLE\s+([0-9A-Za-z\-]+)\.)\s*(.*)$", u, re.IGNORECASE | re.DOTALL)
            if not m:
                parts.append(f"### {u}\n\n")
                continue
            num = m.group(2)
            rest = (m.group(3) or "").strip()
            parts.append(f"### Article {num}.\n\n{rest}\n\n")
        else:
            if not parts:
                parts.append(u + "\n\n")
            else:
                parts[-1] = parts[-1].rstrip() + "\n\n" + u + "\n\n"
    return "".join(parts)


def docx_to_structured_markdown(docx_path: Path) -> str:
    """
    Read Civil Code Base Code.docx-style file and return CIV_structured.md text.
    """
    lines = _iter_docx_paragraph_texts(Path(docx_path))
    lines = _expand_run_in_articles(lines)
    lines = _merge_structure_subtitles(lines)
    return _lines_to_structured_markdown(lines)


def count_articles_in_markdown(md: str) -> int:
    return len(re.findall(r"^###\s+Article\s+", md, re.MULTILINE | re.IGNORECASE))
