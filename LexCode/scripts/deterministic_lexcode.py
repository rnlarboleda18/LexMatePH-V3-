"""
Deterministic LexCode ingestion: **textual fidelity without a generative model**.

**Baseline** — ``parse_rpc_baseline_markdown`` splits ``RPC.md``-style markdown (``##### Article …``)
into discrete articles for the 1932 baseline layer. Regex only; no summarization.

**Amendments** — ``try_deterministic_amendment_parse`` dispatches known files (e.g. RA 6968, RA 10951
Section 6) using fixed slices and string cleanup. Extracted ``new_text`` is normalized with
``normalize_amendment_payload`` (quote stripping, Art. 136 tail guard), not rewritten for style.

**vs. manual JSON** — Structural or highly sensitive laws (e.g. RA 8353 reclassification) use
``manual_amendment_spec.py`` + ``--amendment-json`` so every comma and semicolon in the spec is
stored as provided.

Together with ``article_versions`` rows written by ``process_amendment.apply_amendment_to_database``,
this supports chronological reconstruction: baseline → each Act in order → verifiable history.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RPC_BASELINE_PATH = _REPO_ROOT / "LexCode" / "Codals" / "md" / "RPC.md"

# Filenames with a dedicated offline parser (extend as you add handlers).
DETERMINISTIC_AMENDMENT_BASENAMES: frozenset[str] = frozenset(
    {
        "ra_6968_1990.md",
        "ra_10951_2017.md",
    }
)


def clean_text(text: str) -> str:
    """Normalize common encoding artifacts from scraped / converted markdown."""
    return (
        text.replace("â€“", "-")
        .replace("â€œ", '"')
        .replace("â€", '"')
        .replace("â€™", "'")
    )


def strip_trailing_act_sections_from_rpc136(new_text: str, article_number: str) -> str:
    """
    RA 6968 (and similar) markdown can place Art. 136 before **Section 6** (repealing clause).
    Strip trailing non-codal sections from extracted Art. 136 text.
    """
    if not new_text or str(article_number).strip() != "136":
        return new_text
    t = new_text.replace("\r\n", "\n").strip()
    cut_patterns = [
        r"\n\s*\*\*Section\s+6\.",
        r"\n\s*#{1,6}\s*Section\s+6\.",
        r"\n\s*Section\s+6\.\s*\*?\*?Repealing",
        r"\n\s*-\s*All laws, executive orders, rules and regulations,\s*or any part thereof inconsistent",
        r"\n\s*Approved:\s*",
        r"\n\s*\*\*Section\s+7\.\s*\*?\*?Separability",
    ]
    earliest: int | None = None
    for pat in cut_patterns:
        m = re.search(pat, t, re.IGNORECASE | re.MULTILINE)
        if m:
            earliest = m.start() if earliest is None else min(earliest, m.start())
    if earliest is not None:
        t = t[:earliest].strip()
    t = re.sub(r'\n\s*"\s*$', "", t)
    return t.strip()


def normalize_amendment_payload(result: dict[str, Any], raw_content: str) -> dict[str, Any]:
    """
    Standardize parser output to the shape expected by ``process_amendment`` (same as former ``process_ai_result``).
    """
    cleaned_changes: list[dict[str, Any]] = []
    for change in result.get("changes", []) or []:
        text = (change.get("new_text") or "").strip()
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1].strip()

        text = strip_trailing_act_sections_from_rpc136(text, str(change.get("article_number", "")))

        cleaned_changes.append(
            {
                "article_number": str(change["article_number"]),
                "new_text": text,
                "action": (change.get("action") or "amend").lower(),
            }
        )

    return {
        "amendment_id": result.get("amendment_id"),
        "date": result.get("date"),
        "title": result.get("title"),
        "changes": cleaned_changes,
        "raw_content": raw_content,
    }


# --- RPC baseline (RPC.md) -------------------------------------------------


def parse_rpc_baseline_markdown(content: str) -> list[dict[str, str]]:
    """
    Parse ``RPC.md``-style markdown into article records (regex, no AI).

    Expects headings like: ``##### Article 1. Title.`` followed by body text.
    Returns list of ``{"num", "title", "content"}`` where ``content`` is a single codal block string.
    """
    pattern = r"(##### Article\s+(\d+[A-Za-z-]*)\.\s+(.*?)\.\n\s*(.*?)(?=\n##### Article|\Z))"
    articles: list[dict[str, str]] = []
    for m in re.finditer(pattern, content, re.DOTALL):
        num = m.group(2)
        title = m.group(3).strip()
        body = m.group(4).strip()
        articles.append(
            {
                "num": num,
                "title": title,
                "content": f"Article {num}. {title}. - {body}",
            }
        )
    return articles


# --- RA 6968 offline -------------------------------------------------------


def _slice_ra6968_section_body(content: str, section_num: int) -> str | None:
    nxt = section_num + 1
    m = re.search(
        rf"\*\*Section\s+{section_num}\.\*\*(.*?)(?=\n\*\*Section\s+{nxt}\.)",
        content,
        re.DOTALL | re.IGNORECASE,
    )
    return m.group(1).strip() if m else None


def _ra6968_quoted_payload_to_new_text(section_inner: str) -> str:
    m = re.search(
        r"(?:read as follows:\s*\n+|adding a new article as follows:\s*\n+)(.*)$",
        section_inner,
        re.DOTALL | re.IGNORECASE,
    )
    if not m:
        return ""
    blob = m.group(1).strip()
    cleaned: list[str] = []
    for line in blob.split("\n"):
        s = line.strip()
        if not s:
            continue
        if s.startswith('"'):
            s = s[1:]
        if s.endswith('"'):
            s = s[:-1]
        cleaned.append(s)
    return "\n\n".join(cleaned).strip()


def parse_ra6968_offline(content: str) -> dict[str, Any] | None:
    """
    Deterministic parse of ``ra_6968_1990.md`` (no Gemini). Returns pre-normalize payload or None.
    """
    s2 = _slice_ra6968_section_body(content, 2)
    s3 = _slice_ra6968_section_body(content, 3)
    s4 = _slice_ra6968_section_body(content, 4)
    s5 = _slice_ra6968_section_body(content, 5)
    if not all((s2, s3, s4, s5)):
        return None
    t134 = _ra6968_quoted_payload_to_new_text(s2)
    t134a = _ra6968_quoted_payload_to_new_text(s3)
    t135 = _ra6968_quoted_payload_to_new_text(s4)
    t136 = _ra6968_quoted_payload_to_new_text(s5)
    if not all((t134, t134a, t135, t136)):
        return None
    return {
        "amendment_id": "Republic Act No. 6968",
        "date": "1990-10-24",
        "title": (
            "An Act Punishing the Crime of Coup D′ÉTAT by Amending Articles 134, 135 and 136 "
            "of Chapter One, Title Three of Act No. 3815 (RPC), and for Other Purposes"
        ),
        "changes": [
            {"article_number": "134", "new_text": t134, "action": "amend"},
            {"article_number": "134-A", "new_text": t134a, "action": "insert"},
            {"article_number": "135", "new_text": t135, "action": "amend"},
            {"article_number": "136", "new_text": t136, "action": "amend"},
        ],
    }


# --- RA 10951 offline (Section 6 / Art. 136) --------------------------------


def _ra10951_gt_blockquote_payload_to_plain(payload: str) -> str:
    lines_out: list[str] = []
    for raw_line in payload.split("\n"):
        s = raw_line.strip()
        if not s:
            continue
        if s.startswith(">"):
            s = s[1:].strip()
        if s.startswith('"'):
            s = s[1:]
        if s.endswith('"'):
            s = s[:-1]
        lines_out.append(s)
    return "\n\n".join(lines_out).strip()


def parse_ra10951_offline_rpc_articles_134_to_136(
    filepath: str | Path,
    *,
    content: str | None = None,
) -> dict[str, Any] | None:
    """
    Deterministic extract for RA 10951 as it affects RPC Art. 136 in this repo's markdown.

    Returns normalized payload (same shape as ``parse_amendment_document``) or None.
    """
    path = Path(filepath)
    if content is None:
        content = clean_text(path.read_text(encoding="utf-8"))
    else:
        content = clean_text(content)

    m = re.search(
        r"\*\*Section\s+6\.\*\*(.*?)(?=\n\*\*Section\s+7\.)",
        content,
        re.DOTALL | re.IGNORECASE,
    )
    if not m:
        return None
    inner = m.group(1)
    if not re.search(r"Article\s+136", inner, re.IGNORECASE):
        return None
    m2 = re.search(
        r"hereby\s+amended\s+to\s+read\s+as\s+follows:\s*\n+(.*)$",
        inner,
        re.DOTALL | re.IGNORECASE,
    )
    if not m2:
        return None
    payload = m2.group(1).strip()
    t136 = _ra10951_gt_blockquote_payload_to_plain(payload)
    if not t136:
        return None
    raw = {
        "amendment_id": "Republic Act No. 10951",
        "date": "2017-08-29",
        "title": (
            "An Act Adjusting the Amount or the Value of Property and Damage on Which a Penalty is "
            "Based and the Fines Imposed Under the Revised Penal Code (RA 10951)"
        ),
        "changes": [{"article_number": "136", "new_text": t136, "action": "amend"}],
    }
    return normalize_amendment_payload(raw, content)


def try_deterministic_amendment_parse(
    filepath: str | Path,
    *,
    content: str | None = None,
) -> dict[str, Any] | None:
    """
    If *filepath* has a registered offline handler, return normalized amendment payload; else None.

    Pass *content* when the file was already read to avoid a second disk read.
    """
    path = Path(filepath)
    base = path.name.lower()
    try:
        text = clean_text(content) if content is not None else clean_text(path.read_text(encoding="utf-8"))
    except OSError:
        return None

    if base == "ra_6968_1990.md":
        raw = parse_ra6968_offline(text)
        return normalize_amendment_payload(raw, text) if raw else None

    if base == "ra_10951_2017.md":
        return parse_ra10951_offline_rpc_articles_134_to_136(path, content=text)

    return None


def is_deterministic_amendment_file(filepath: str | Path) -> bool:
    return Path(filepath).name.lower() in DETERMINISTIC_AMENDMENT_BASENAMES


def main(argv: list[str] | None = None) -> int:
    """CLI: ``baseline`` or ``amendment`` subcommands (parse-only, no DB)."""
    argv = argv if argv is not None else sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        print(
            "Usage:\n"
            "  python deterministic_lexcode.py baseline [--path PATH_TO_RPC.md]\n"
            "  python deterministic_lexcode.py amendment <path_to_amendment.md>\n"
            "Prints JSON summary (article counts or amendment metadata) to stdout."
        )
        return 0 if argv else 1

    cmd = argv[0]
    if cmd == "baseline":
        import argparse

        p = argparse.ArgumentParser(prog="deterministic_lexcode baseline")
        p.add_argument(
            "--path",
            type=Path,
            default=DEFAULT_RPC_BASELINE_PATH,
            help=f"Default: {DEFAULT_RPC_BASELINE_PATH}",
        )
        args = p.parse_args(argv[1:])
        if not args.path.is_file():
            print(f"File not found: {args.path}", file=sys.stderr)
            return 1
        articles = parse_rpc_baseline_markdown(args.path.read_text(encoding="utf-8"))
        print(json.dumps({"path": str(args.path), "article_count": len(articles)}, indent=2))
        return 0

    if cmd == "amendment":
        if len(argv) < 2:
            print("amendment requires a path", file=sys.stderr)
            return 1
        apath = Path(argv[1])
        if not apath.is_file():
            print(f"File not found: {apath}", file=sys.stderr)
            return 1
        out = try_deterministic_amendment_parse(apath)
        if out is None:
            print(
                json.dumps(
                    {
                        "path": str(apath),
                        "deterministic": False,
                        "note": "No offline handler for this file (use AI parse_amendment_document).",
                    },
                    indent=2,
                )
            )
            return 2
        summary = {
            "path": str(apath),
            "deterministic": True,
            "amendment_id": out.get("amendment_id"),
            "date": out.get("date"),
            "changes_count": len(out.get("changes") or []),
        }
        print(json.dumps(summary, indent=2))
        return 0

    print(f"Unknown command: {cmd}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
