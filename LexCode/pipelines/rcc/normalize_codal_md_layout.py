"""
Normalize codal Markdown exported from Word (e.g. Revised Corporation Code).

1. **Header hierarchy** — Blank line before each `##` / `###` / `#` heading (except
   file start). Blank line after a heading when the next line is body text (not
   another heading), matching `CIV_structured.md` layout for ingest parsers.
2. **Glued paragraphs** — Lines like `...here.It continues` become two paragraphs
   (`...here.` + blank + `It continues`).
3. **Whitespace** — Collapse 3+ consecutive newlines to 2.

Usage:
  python normalize_codal_md_layout.py LexCode/Codals/md/RCC_raw.md -o LexCode/Codals/md/RCC_structured.md

Export Word to UTF-8 text or Markdown first; this script does not read .docx.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


HEADING_RE = re.compile(r"^(#{1,6})\s+")
# Lowercase/digit/paren before period; capital letter starts next word (min 3 letters).
# Word-ending lowercase + period + new sentence (capital); avoids `5.The` (digit before dot).
GLUED_SENTENCE_RE = re.compile(r"(?<=[a-z\)\]])\.(?=[A-Z][a-z]{2,}\b)")
MULTI_BLANK_RE = re.compile(r"\n{3,}")


def split_glued_sentences_in_line(line: str) -> list[str]:
    if not line.strip() or line.lstrip().startswith("#"):
        return [line]
    s = GLUED_SENTENCE_RE.sub(".\n\n", line)
    return s.split("\n")


def normalize_block(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    raw_lines = text.split("\n")
    lines: list[str] = []
    for L in raw_lines:
        lines.extend(split_glued_sentences_in_line(L))

    out: list[str] = []
    for i, line in enumerate(lines):
        is_head = bool(HEADING_RE.match(line))
        if is_head:
            if out and out[-1].strip() != "":
                out.append("")
            elif len(out) >= 2 and out[-1] == "" and out[-2] == "":
                out.pop()
        out.append(line)
        if is_head:
            j = i + 1
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            if j < len(lines):
                nxt = lines[j]
                if nxt.strip() and not nxt.lstrip().startswith("#") and j == i + 1:
                    out.append("")
    body = "\n".join(out)
    body = MULTI_BLANK_RE.sub("\n\n", body)
    return body.strip() + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="Normalize Word-exported codal Markdown layout.")
    ap.add_argument("input", type=Path, help="Source .md or .txt (UTF-8)")
    ap.add_argument("-o", "--output", type=Path, required=True, help="Output .md path")
    args = ap.parse_args()
    raw = args.input.read_text(encoding="utf-8", errors="replace")
    fixed = normalize_block(raw)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(fixed, encoding="utf-8", newline="\n")
    print(f"Wrote {args.output} ({len(fixed)} chars)")


if __name__ == "__main__":
    main()
