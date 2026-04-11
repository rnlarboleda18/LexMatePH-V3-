"""
Convert Supreme Court E-Library style RA 11232 export (plain TITLE / SEC. lines)
into RCC_structured.md for 3_ingest_codal_reference.py.

Maps each SEC./SECTION N to ### Article N. (LexCode uses article rows for code sections.)
Emits ## BOOK I, ## TITLE <roman> <label>, ## CHAPTER <n> <label> as needed.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

# Start capturing after enacting clause (skip site chrome above it)
START_MARKERS = (
    "in congress assembled",
    "[ republic act no. 11232",
    "republic act no. 11232",
)

# Stop before signature tables / approval footer
STOP_MARKERS = (
    "| (sgd.)",
    "approved:",
    "this act which is a consolidation",
)


def _norm_line(s: str) -> str:
    return s.replace("\ufeff", "").strip()


def _is_noise(line: str) -> bool:
    t = line.strip()
    if not t:
        return False
    if t.startswith("|") and "---" in t:
        return True
    if t.startswith("!["):
        return True
    return False


def convert(text: str) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: list[str] = []
    i = 0
    started = False
    while i < len(lines):
        raw = lines[i]
        line = _norm_line(raw)
        low = line.lower()
        if not started:
            if any(m in low for m in START_MARKERS):
                started = True
                out.append("## BOOK I REVISED CORPORATION CODE OF THE PHILIPPINES\n")
                out.append("\n")
            i += 1
            continue
        if any(low.startswith(m) for m in STOP_MARKERS):
            break
        if _is_noise(line):
            i += 1
            continue

        m_title = re.match(r"^TITLE\s+([IVXLCDM]+)\s*$", line, re.I)
        if m_title:
            roman = m_title.group(1).upper()
            bits = [roman]
            j = i + 1
            while j < len(lines):
                nxt = _norm_line(lines[j])
                if not nxt:
                    j += 1
                    continue
                low_n = nxt.lower()
                if re.match(r"^TITLE\s+", nxt, re.I):
                    break
                if re.match(r"^CHAPTER\s+", nxt, re.I):
                    break
                if re.match(r"^(?:SEC\.|SECTION)\s*\d+", nxt, re.I):
                    break
                if any(low_n.startswith(m) for m in STOP_MARKERS):
                    break
                bits.append(re.sub(r"\s+", " ", nxt))
                j += 1
            label = " ".join(bits[1:]) if len(bits) > 1 else ""
            out.append(f"## TITLE {roman} {label}\n".rstrip() + "\n\n")
            i = j
            continue

        m_ch = re.match(r"^CHAPTER\s+([IVXLCDM0-9]+)\s*$", line, re.I)
        if m_ch:
            ch = m_ch.group(1).upper()
            bits = [ch]
            j = i + 1
            while j < len(lines):
                nxt = _norm_line(lines[j])
                if not nxt:
                    j += 1
                    continue
                low_n = nxt.lower()
                if re.match(r"^TITLE\s+", nxt, re.I):
                    break
                if re.match(r"^CHAPTER\s+", nxt, re.I):
                    break
                if re.match(r"^(?:SEC\.|SECTION)\s*\d+", nxt, re.I):
                    break
                if any(low_n.startswith(m) for m in STOP_MARKERS):
                    break
                bits.append(re.sub(r"\s+", " ", nxt))
                j += 1
            label = " ".join(bits[1:]) if len(bits) > 1 else ""
            out.append(f"## CHAPTER {ch} {label}\n".rstrip() + "\n\n")
            i = j
            continue

        # E-Library uses "SECTION 1\._" or "SEC. 2\._" or "SEC. 8, _"
        m_sec = re.match(
            r"^(?:SEC\.|SECTION)\s*(\d+)(?:\\\.|\.|,)\s*(.*)$",
            line,
            re.I,
        )
        if m_sec:
            num = m_sec.group(1)
            rest = (m_sec.group(2) or "").strip()
            rest = re.sub(r"\\([._\-])", r"\1", rest)
            out.append(f"### Article {num}.\n\n")
            if rest:
                out.append(rest + "\n\n")
            i += 1
            while i < len(lines):
                nxt_raw = lines[i]
                nxt = _norm_line(nxt_raw)
                low_n = nxt.lower()
                if not nxt:
                    out.append("\n")
                    i += 1
                    continue
                if re.match(r"^TITLE\s+", nxt, re.I):
                    break
                if re.match(r"^CHAPTER\s+", nxt, re.I):
                    break
                if re.match(r"^(?:SEC\.|SECTION)\s*\d+", nxt, re.I):
                    break
                if any(low_n.startswith(m) for m in STOP_MARKERS):
                    break
                if _is_noise(nxt):
                    i += 1
                    continue
                out.append(nxt_raw.rstrip() + "\n")
                i += 1
            out.append("\n")
            continue

        i += 1

    body = "".join(out)
    body = re.sub(r"\n{4,}", "\n\n\n", body)
    return body.strip() + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", type=Path, help="E-Library export .md")
    ap.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("LexCode/Codals/md/RCC_structured.md"),
        help="Output path (default: LexCode/Codals/md/RCC_structured.md)",
    )
    args = ap.parse_args()
    src = args.input.resolve()
    if not src.is_file():
        raise SystemExit(f"Missing input: {src}")
    text = src.read_text(encoding="utf-8", errors="replace")
    md = convert(text)
    out = args.output.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8", newline="\n")
    n_art = len(re.findall(r"^### Article \d+\.", md, re.M))
    print(f"Wrote {out} ({n_art} sections)")


if __name__ == "__main__":
    main()
