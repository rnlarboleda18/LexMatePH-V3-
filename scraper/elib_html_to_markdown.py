"""
E-Library (elibrary.judiciary.gov.ph) decision HTML → clean Markdown.

Strips site chrome (nav, contact tables, footers) and keeps the decision body
starting at EN BANC / division headings or the first case-number header block.

Output begins at that heading (no Source URL / document ID block on top).
Optional provenance: pass include_source_header=True to append a --- footer.

Letter-spaced "D E C I S I O N" merged into the ### case caption is split so
the caption ends on its own ### line and "Decision" appears on the next line.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple

from bs4 import BeautifulSoup
from markdownify import markdownify as md

# Pages that return HTTP 200 but no decision body
ELIB_ERROR_MARKERS = (
    "Document not available on the database",
    "Document Search Error",
    "Document not available",
    "please call the SC Library",
)

# Decision body usually starts with one of these headings (markdownified)
_START_HEADING = re.compile(
    r"(?ms)^##\s*("
    r"EN BANC|"
    r"FIRST DIVISION|SECOND DIVISION|THIRD DIVISION|"
    r"SPECIAL THIRD DIVISION|SPECIAL DIVISION|"
    r"RESOLUTION"
    r")\s*$",
    re.IGNORECASE,
)

_START_CASE_HEADER = re.compile(
    r"(?ms)^##\s*\[\s*(G\.R\.|A\.M\.|A\.C\.|U\.D\.|B\.M\.|A\.T\.O\.|P\.E\.T\.|E\.M\.)",
    re.IGNORECASE,
)


def is_elib_error_page(html: str) -> bool:
    if not html or not html.strip():
        return True
    lower = html.lower()
    for m in ELIB_ERROR_MARKERS:
        if m.lower() in lower:
            return True
    return False


def _strip_nav_noise(soup: BeautifulSoup) -> None:
    for tag in soup(["script", "style", "link", "meta", "iframe", "noscript"]):
        tag.decompose()

    for table in soup.find_all("table"):
        text = table.get_text(" ", strip=True)
        if "CONTACT:" in text and "libraryservices.sc@" in text.replace(" ", ""):
            table.decompose()

    for h4 in soup.find_all("h4"):
        t = h4.get_text(strip=True)
        if t == "Foreign Supreme Courts":
            parent = h4.find_parent(["div", "td", "section", "article"])
            if parent:
                parent.decompose()
            else:
                h4.decompose()


_SPACED_DECISION_SUFFIX = re.compile(r"D\s*E\s*C\s*I\s*S\s*I\s*O\s*N\s*$", re.IGNORECASE)
_SPACED_RESOLUTION_SUFFIX = re.compile(
    r"R\s+E\s+S\s+O\s+L\s+U\s+T\s+I\s+O\s+N\s*$", re.IGNORECASE
)


def _split_decision_from_case_title_line(md_text: str) -> str:
    """
    E-Library titles often render as one ### line ending with letter-spaced
    'D E C I S I O N' or 'R E S O L U T I O N'. Put the caption on one ### line and
    ``### Decision`` / ``### Resolution`` on the next so app CSS (e.g. ``.prose h3``)
    centers them when rendered.
    """
    lines = md_text.splitlines()
    out: list[str] = []
    for line in lines:
        if line.startswith("### "):
            matched = False
            for suffix_re, heading in (
                (_SPACED_DECISION_SUFFIX, "### Decision"),
                (_SPACED_RESOLUTION_SUFFIX, "### Resolution"),
            ):
                m = suffix_re.search(line)
                if m:
                    prefix = line[: m.start()].rstrip()
                    if prefix.startswith("### ") and len(prefix) > 4:
                        out.append(prefix)
                        out.append("")
                        out.append(heading)
                        matched = True
                        break
            if matched:
                continue
        out.append(line)
    return "\n".join(out)


def _trim_markdown_preface(md_text: str) -> str:
    """Remove duplicated site chrome before the real decision heading."""
    m = _START_HEADING.search(md_text)
    if m:
        return md_text[m.start() :].strip()

    m2 = _START_CASE_HEADER.search(md_text)
    if m2:
        return md_text[m2.start() :].strip()

    # Fallback: first "D E C I S I O N" line that is not part of a long paragraph
    for line in md_text.splitlines():
        stripped = line.strip()
        if re.match(r"^#*\s*D\s*E\s*C\s*I\s*S\s*I\s*O\s*N\s*$", stripped, re.I):
            idx = md_text.find(line)
            if idx >= 0:
                tail = md_text[idx:].strip()
                # If next meaningful content is still nav, try EN BANC inside tail
                m3 = _START_HEADING.search(tail)
                if m3:
                    return tail[m3.start() :].strip()
                return tail
    return md_text.strip()


def _trim_markdown_footer(md_text: str) -> str:
    cut_markers = (
        "\n© Supreme Court E-Library",
        "\nThis website was designed and developed",
        "\n#### Foreign Supreme Courts",
        "\n| CONTACT:",
    )
    out = md_text
    for marker in cut_markers:
        pos = out.find(marker)
        if pos != -1:
            out = out[:pos].rstrip()
    return out.strip()


def _simple_footnote_markers(md_text: str) -> str:
    """Turn [1] into [^1] and line-start [^1] text into [^1]: for definitions."""

    def repl(m: re.Match[str]) -> str:
        return f"[^{m.group(1)}]"

    text = re.sub(r"\[(\d+)\]", repl, md_text)

    def def_repl(m: re.Match[str]) -> str:
        return f"[^{m.group(1)}]:"

    text = re.sub(r"^\[\^(\d+)\]\s+", def_repl, text, flags=re.MULTILINE)
    return text


def elib_html_to_markdown(
    html: str,
    *,
    source_url: Optional[str] = None,
    elib_doc_id: Optional[int] = None,
    include_source_header: bool = False,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Convert one E-Library showdocs HTML document to Markdown.

    Returns (markdown, error). markdown is None when the page is an error/empty
    document; error is a short reason string.
    """
    if is_elib_error_page(html):
        return None, "elib_error_or_empty"

    soup = BeautifulSoup(html, "html.parser")
    _strip_nav_noise(soup)

    content_div = soup.find("div", id="content") or soup.body
    if not content_div:
        return None, "no_content_div"

    inner_md = md(
        str(content_div),
        heading_style="ATX",
        strip=["img"],
    )
    inner_md = _trim_markdown_preface(inner_md)
    inner_md = _trim_markdown_footer(inner_md)
    inner_md = re.sub(r"View printer friendly version", "", inner_md, flags=re.I)
    inner_md = re.sub(r"The Lawphil Project - Arellano Law Foundation", "", inner_md, flags=re.I)
    inner_md = re.sub(r"\n{3,}", "\n\n", inner_md).strip()
    inner_md = _simple_footnote_markers(inner_md)
    inner_md = _split_decision_from_case_title_line(inner_md)

    title_tag = soup.find("title")
    page_title = title_tag.get_text(strip=True) if title_tag else ""

    if not include_source_header:
        return inner_md, None

    # Provenance after the decision body so the file starts at EN BANC / division.
    footer: list[str] = ["", "---", ""]
    if source_url:
        footer.append(f"Source URL: {source_url}")
    if elib_doc_id is not None:
        footer.append(f"E-Library document ID: {elib_doc_id}")
    if page_title:
        footer.append(f"Title: {page_title}")
    return inner_md + "\n" + "\n".join(footer), None


def _self_test() -> None:
    err_html = "<html><body><h4>Document Search Error</h4>Document not available</body></html>"
    assert is_elib_error_page(err_html)
    md_out, err = elib_html_to_markdown(err_html, source_url="https://example/1")
    assert md_out is None and err == "elib_error_or_empty"

    good = """
    <html><head><title>Test Case Title</title></head><body>
    <div id="content">
    <table><tr><td>CONTACT:</td><td>libraryservices.sc@judiciary.gov.ph</td></tr></table>
    <p>noise</p>
    <h2>EN BANC</h2>
    <h2>[ G.R. No. 1, January 1, 2020 ]</h2>
    <p>Body text with footnote[1] here.</p>
    </div></body></html>
    """
    md_ok, err2 = elib_html_to_markdown(
        good,
        source_url="https://elibrary.example/showdocs/1/1",
        elib_doc_id=1,
        include_source_header=True,
    )
    assert err2 is None and md_ok
    assert md_ok.strip().startswith("## EN BANC")
    assert "Source URL:" in md_ok
    assert "E-Library document ID: 1" in md_ok
    assert "Title: Test Case Title" in md_ok
    assert "## EN BANC" in md_ok
    assert "CONTACT:" not in md_ok
    assert "libraryservices" not in md_ok.lower()

    md_clean, err3 = elib_html_to_markdown(good, elib_doc_id=1, include_source_header=False)
    assert err3 is None and md_clean.strip().startswith("## EN BANC")
    assert "Source URL:" not in md_clean

    caption = (
        "## EN BANC\n\n## [ G.R. No. 1, January 1, 2020 ]\n\n"
        "### PARTY A VS. PARTY B, RESPONDENT.D E C I S I O N\n\nNext"
    )
    split = _split_decision_from_case_title_line(caption)
    assert "### PARTY A VS. PARTY B, RESPONDENT." in split
    assert "\n### Decision\n" in split
    assert "RESPONDENT.D E C I S I O N" not in split

    caption_res = (
        "## EN BANC\n\n## [ G.R. No. 2 ]\n\n"
        "### PARTY A VS. PARTY B, RESPONDENTS. R E S O L U T I O N\n\nNext"
    )
    split_res = _split_decision_from_case_title_line(caption_res)
    assert "### PARTY A VS. PARTY B, RESPONDENTS." in split_res
    assert "\n### Resolution\n" in split_res
    assert "RESPONDENTS. R E S O L U T I O N" not in split_res

    print("elib_html_to_markdown self-test OK")


if __name__ == "__main__":
    _self_test()
