"""
Normalize codal Markdown exported from Word (e.g. Revised Corporation Code).

1. **Header hierarchy** — Blank line before each `##` / `###` / `#` heading (except
   file start). Blank line after a heading when the next line is body text (not
   another heading), matching `CIV_structured.md` layout for ingest parsers.
2. **Glued paragraphs** — Lines like `...here.It continues` become two paragraphs
   (`...here.` + blank + `It continues`).
3. **Whitespace** — Collapse 3+ consecutive newlines to 2.
4. **RCC Section 14 form (when detected)** — Promotes floating `Name` / `Nationality` /
   `Residence` lines into the next GFM table header row, shortens long underscore
   cells, inserts the subscriber table when missing, and replaces the `IN WITNESS WHEREOF`
   signature run-on with compact GFM tables.

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
# Long underscore / em-dash placeholder runs in E-Library / Word exports (form lines).
_LONG_PLACEHOLDER = re.compile(r"_{6,}")


def split_glued_sentences_in_line(line: str) -> list[str]:
    if not line.strip() or line.lstrip().startswith("#"):
        return [line]
    s = GLUED_SENTENCE_RE.sub(".\n\n", line)
    return s.split("\n")


def _needs_rcc_section14_form_fixes(text: str) -> bool:
    return (
        "Articles of Incorporation of" in text or "Form of Articles of Incorporation" in text
    ) and ("### Section 14." in text or "### Article 14." in text)


def _split_pipe_row(line: str) -> list[str]:
    s = line.strip()
    if not s.startswith("|"):
        return []
    if not s.endswith("|"):
        s = s + "|"
    inner = s[1:-1]
    return [c.strip() for c in inner.split("|")]


def _join_pipe_row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def _shorten_placeholder_cell(cell: str, width: int = 8) -> str:
    t = cell.strip()
    if not t:
        return "_" * width
    if _LONG_PLACEHOLDER.fullmatch(t.replace(" ", "")) or (
        "_" in t and len(t) > 24 and set(t.replace(" ", "")) <= {"_", " "}
    ):
        return "_" * width
    return _LONG_PLACEHOLDER.sub("_" * width, t)


def _shorten_pipe_row(line: str) -> str:
    cells = _split_pipe_row(line)
    if not cells:
        return line
    return _join_pipe_row([_shorten_placeholder_cell(c) for c in cells])


def _replace_floating_labels_and_table(
    body: str,
    anchor: str,
    header_cells: list[str],
) -> str:
    """Merge floating column labels into the following pipe table; shorten wide underscore cells."""
    while anchor in body:
        left, right = body.split(anchor, 1)
        lines = right.split("\n")
        table_lines: list[str] = []
        i = 0
        while i < len(lines) and lines[i].strip().startswith("|"):
            table_lines.append(lines[i])
            i += 1
        if len(table_lines) < 2:
            break
        sep_idx = 1 if len(table_lines) > 1 and "---" in table_lines[1] else 0
        if sep_idx == 0 or "---" not in table_lines[sep_idx]:
            break
        data_rows = table_lines[sep_idx + 1 :]
        n = len(header_cells)
        header = _join_pipe_row(header_cells)
        sep = _join_pipe_row(["---"] * n)
        rebuilt = [header, sep]
        for row in data_rows:
            cells = _split_pipe_row(row)
            if len(cells) < n:
                cells = cells + [""] * (n - len(cells))
            elif len(cells) > n:
                cells = cells[:n]
            rebuilt.append(_join_pipe_row([_shorten_placeholder_cell(c) for c in cells]))
        new_table = "\n".join(rebuilt)
        remainder = "\n".join(lines[i:])
        body = left + new_table + "\n" + remainder
    return body


def _insert_subscriber_table_if_no_pipe_table(text: str) -> str:
    """Eighth-clause labels sometimes have no following pipe table in E-Library exports."""
    anchor = (
        "Name of Subscriber\n\nNationality\n\nNo. of Shares Subscribed\n\n"
        "Amount Subscribed\n\nAmount Paid\n\n"
    )
    if anchor not in text:
        return text
    left, right = text.split(anchor, 1)
    if right.lstrip().startswith("|"):
        return text
    tbl = (
        "| Name of Subscriber | Nationality | No. of Shares Subscribed | Amount Subscribed | Amount Paid |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| ________ | ________ | ________ | ________ | ________ |\n"
        "| ________ | ________ | ________ | ________ | ________ |\n\n"
    )
    return left + tbl + right


def _repair_split_pipe_incorporator_headers(text: str) -> str:
    """Merge `| Name` / `| Nationality` / `| Residence` single-pipe lines (broken SC exports)."""
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(
        r"(^|\n)\|\s*Name\s*\n\|\s*Nationality\s*\n\|\s*Residence\s*(?=\n\|)",
        r"\1| Name | Nationality | Residence |",
        t,
    )
    t = re.sub(
        r"(^|\n)\|\s*Name of Subscriber\s*\n\|\s*Nationality\s*\n\|\s*No\.\s*of Shares Subscribed\s*\n"
        r"\|\s*Amount Subscribed\s*\n\|\s*Amount Paid\s*(?=\n\|)",
        r"\1| Name of Subscriber | Nationality | No. of Shares Subscribed | Amount Subscribed | Amount Paid |",
        t,
        flags=re.IGNORECASE,
    )
    t = re.sub(
        r"(IN WITNESS WHEREOF[^\n]+?)(\b20)\s+(in the City/Municipality)",
        r"\1\2____ \3",
        t,
        flags=re.IGNORECASE,
    )
    return t


def fix_rcc_section14_form_tables(text: str) -> str:
    """
    RCC Section 14 form: E-Library exports put Name/Nationality/Residence above pipe tables,
    and use very long underscore cells (desktop overflow). Promote labels into GFM headers
    and compact placeholder cells; normalize IN WITNESS signature block.
    """
    t = _repair_split_pipe_incorporator_headers(text)
    t = _replace_floating_labels_and_table(
        t,
        "Name\n\nNationality\n\nResidence\n\n",
        ["Name", "Nationality", "Residence"],
    )
    t = _replace_floating_labels_and_table(
        t,
        "Name of Subscriber\n\nNationality\n\nNo. of Shares Subscribed\n\nAmount Subscribed\n\nAmount Paid\n\n",
        [
            "Name of Subscriber",
            "Nationality",
            "No. of Shares Subscribed",
            "Amount Subscribed",
            "Amount Paid",
        ],
    )
    t = _insert_subscriber_table_if_no_pipe_table(t)
    # IN WITNESS paragraph + one long signature line → compact paragraph + GFM tables
    wit = re.compile(
        r"(IN WITNESS WHEREOF,[^\n]+)\n\n([^\n]+)\n\n(?=###\s+(?:Section|Article)\s+15\.)",
        re.MULTILINE,
    )

    def _wit_repl(m: re.Match[str]) -> str:
        para = _LONG_PLACEHOLDER.sub("________", m.group(1))
        sig_table = (
            "\n\n| Signature | Signature | Signature |\n"
            "| --- | --- | --- |\n"
            "| ________ | ________ | ________ |\n"
            "| ________ | ________ | ________ |\n"
            "| ________ | ________ | ________ |\n"
            "| ________ | ________ | ________ |\n"
            "| ________ | ________ | ________ |\n\n"
            "*(Names and signatures of the incorporators)*\n\n"
            "| Treasurer |\n| --- |\n| ________ |\n\n"
            "*(Name and signature of Treasurer)*\n\n"
        )
        return para + sig_table

    t = wit.sub(_wit_repl, t)
    return t


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
    if _needs_rcc_section14_form_fixes(body):
        body = fix_rcc_section14_form_tables(body)
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
