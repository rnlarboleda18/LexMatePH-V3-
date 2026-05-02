"""
Deterministic guards for RPC full-AI amendment ingest.

Use before calling apply_amendment_with_ai so mis-extractions (RA 6425 sections filed as
RPC articles, Sec. headings, hallucinated article numbers) fail closed.
"""

from __future__ import annotations

import re


def _strip_leading_quote(s: str) -> str:
    t = (s or "").lstrip()
    if t.startswith(('"', "'")):
        t = t[1:].lstrip()
    return t


def quoted_line_smells_non_rpc_article(new_text: str) -> str | None:
    """
    Return a skip reason if the extracted quote cannot be an RPC article block; else None.
    """
    t = _strip_leading_quote(new_text)
    if not t:
        return "Empty new_text — skipped."

    if re.match(r"^Section\s+\d+", t, re.I):
        return "Quoted text begins with 'Section …' (special-law / organic-act form), not RPC 'Art. …'."

    if re.match(r"^Sec\.\s*\d", t, re.I):
        return (
            "Quoted text begins with 'Sec. …' (typical RA 6425 / special-law section), "
            "not RPC 'Art. …' — skipped."
        )

    low = t.lower()
    head = low[:800]
    if "republic act no. 6425" in head or "dangerous drugs act of 1972" in head:
        return "Quoted text references RA 6425 / Dangerous Drugs Act — not an RPC article row."

    if "manufacture of regulated drugs" in head and "regulated drug" in head:
        return "Quoted text looks like a Dangerous Drugs Act manufacture provision — not RPC."

    if "plea-bargaining provisions" in head and "reclusion perpetua to death" in head:
        if "this act" in head or "any provision of this act" in head:
            return "Quoted text looks like RA 6425 Sec. 20-A (plea bargaining) — not RPC."

    return None


def _collapse_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def source_markdown_evidence_for_rpc_article(
    md: str, article_num: str, new_text: str
) -> str | None:
    """
    Return None if the source file plausibly amends this RPC article; else a skip reason.

    Requires either an explicit ``Art. N`` / ``Article N`` reference for this article number
    in the markdown, or a long enough verbatim snippet of new_text found in the file.
    """
    if not (md or "").strip():
        return None

    art = str(article_num).strip()
    if not art:
        return "Missing article number for source check."

    escaped = re.escape(art)
    # "Art. 114", "Article 114", "Articles 337 and 338" (plural amendatory clauses)
    anchor = re.compile(rf"(?:Art\.|Articles?)\s+{escaped}(?:\b|[.\s\-,])", re.I)
    if anchor.search(md):
        return None

    nt = _strip_leading_quote(new_text)
    snippet = _collapse_ws(nt[:160])
    if len(snippet) >= 36 and snippet.lower() in _collapse_ws(md).lower():
        return None

    return (
        f"Source markdown has no 'Art./Article {art}' anchor and no long verbatim snippet match — "
        "likely wrong article number or wrong statute; skipped."
    )


def validate_rpc_change_for_ingest(
    new_text: str,
    article_num: str,
    source_markdown: str | None,
) -> tuple[bool, str | None]:
    """
    Run all quote-level checks and optional source markdown check.

    Returns:
        (ok, skip_reason)
    """
    r = quoted_line_smells_non_rpc_article(new_text)
    if r:
        return False, r
    if source_markdown is not None:
        r2 = source_markdown_evidence_for_rpc_article(source_markdown, article_num, new_text)
        if r2:
            return False, r2
    return True, None


if __name__ == "__main__":
    # Self-checks (run: python amendment_ingest_guards.py)
    assert quoted_line_smells_non_rpc_article('Sec. 14-A. Manufacture of Regulated Drugs.') is not None
    assert quoted_line_smells_non_rpc_article("Article 114. Treason.") is None
    md = '**Section 2.** Article 114 of the Revised Penal Code is hereby amended:\n"Art. 114. Treason."'
    assert source_markdown_evidence_for_rpc_article(md, "114", "Art. 114. Treason.") is None
    md2 = "**Section 2.** Articles 337 and 338 of Act 3815 are hereby amended"
    assert source_markdown_evidence_for_rpc_article(md2, "337", "Article 337. Qualified seduction.") is None
    assert source_markdown_evidence_for_rpc_article(md, "999", "Art. 999. Fake.") is not None
    print("amendment_ingest_guards ok")
