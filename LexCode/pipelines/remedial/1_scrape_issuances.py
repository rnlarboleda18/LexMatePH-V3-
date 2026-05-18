"""
Step 1 — Scrape Remedial Law SC issuances and statutes.

Sources:
  LawPhil (HTML)    — 5 laws via standard browser UA
  Chanrobles (HTML) — CPRA (chanroblesvirtualawlibrary watermarks stripped)
  GoSupra (HTML)    — NCJC (prerendered via Googlebot UA)
  SC Judiciary PDF  — Notarial Practice (pypdf extraction)
  LawPhil (HTML)    — RA-11642

Saves flat cleaned-text MD files to LexCode/Codals/md/remedial/.
Saves raw HTML/PDF to LexCode/Codals/html/remedial/.
Run once; skips files already present.
"""
from __future__ import annotations

import io
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

_REPO_ROOT = Path(__file__).resolve().parents[3]
HTML_DIR   = _REPO_ROOT / "LexCode" / "Codals" / "html" / "remedial"
MD_DIR     = _REPO_ROOT / "LexCode" / "Codals" / "md"   / "remedial"

# ── User-Agents ───────────────────────────────────────────────────────────────
_UA_BROWSER = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
_UA_BOT     = "Googlebot/2.1 (+http://www.google.com/bot.html)"

# ── Statute list ──────────────────────────────────────────────────────────────
STATUTES = [
    {
        "statute_id": "AM-07-9-12-SC",
        "label":      "Rule on the Writ of Amparo (A.M. No. 07-9-12-SC)",
        "url":        "https://lawphil.net/judjuris/juri2007/sep2007/am_07-9-12-sc_2007.html",
        "filename":   "am_07_9_12_sc_2007",
        "source":     "lawphil",
    },
    {
        "statute_id": "AM-08-1-16-SC",
        "label":      "Rule on the Writ of Habeas Data (A.M. No. 08-1-16-SC)",
        "url":        "https://lawphil.net/judjuris/juri2008/jan2008/am_08-1-16_sc_2008.html",
        "filename":   "am_08_1_16_sc_2008",
        "source":     "lawphil",
    },
    {
        "statute_id": "AM-09-6-8-SC",
        "label":      "Rules of Procedure for Environmental Cases — Kalikasan (A.M. No. 09-6-8-SC)",
        "url":        "https://www.lawphil.net/courts/supreme/am/am_09-6-8-sc_2010.html",
        "filename":   "am_09_6_8_sc_2010",
        "source":     "lawphil",
    },
    {
        "statute_id": "AM-01-7-01-SC",
        "label":      "Rules on Electronic Evidence (A.M. No. 01-7-01-SC)",
        "url":        "https://lawphil.net/courts/supreme/am/am_01-7-01_sc_2001.html",
        "filename":   "am_01_7_01_sc_2001",
        "source":     "lawphil",
    },
    {
        "statute_id": "CPRA",
        "label":      "Code of Professional Responsibility and Accountability (A.M. No. 22-09-01-SC)",
        "url":        "https://chanrobles.com/rulesofcourt/2023codeofprofessionalresponsibility.php",
        "filename":   "am_22_09_01_sc_2023",
        "source":     "chanrobles",
    },
    {
        "statute_id": "AM-02-8-13-SC",
        "label":      "2004 Rules on Notarial Practice (A.M. No. 02-8-13-SC)",
        "url":        "https://chanrobles.com/supremecourtamno02-8-13-sc2004.html",
        "filename":   "am_02_8_13_sc_2004",
        "source":     "chanrobles",
    },
    {
        "statute_id": "NCJC",
        "label":      "New Code of Judicial Conduct for the Philippine Judiciary (A.M. No. 03-05-01-SC)",
        "url":        "https://source.gosupra.com/docs/statute/1251/",
        "filename":   "am_03_05_01_sc_2004",
        "source":     "gosupra",
    },
    {
        "statute_id": "RA-11642",
        "label":      "Republic Act No. 11642 — Domestic Administrative Adoption and Alternative Child Care Act",
        "url":        "https://lawphil.net/statutes/repacts/ra2022/ra_11642_2022.html",
        "filename":   "ra_11642_2022",
        "source":     "lawphil",
    },
]

# ── LawPhil watermarks ────────────────────────────────────────────────────────
_LAWPHIL_WATERMARKS = [
    r"The Lawphil Project\s*[-–—]\s*Arellano Law Foundation",
    r"The Lawphil Project",
    r"Arellano Law Foundation",
    r"ℒαwρhi৷",
    r"ℒαwρhi",
    r"1awp\+\+i1",
    r"1avvphi1",
    r"1wphi1",
    r"Lawphil",
    r"\(awÞhi\(",
    r"\(awÞhi",
    r"1a\w+phi1",
]

# ── Chanrobles watermarks ─────────────────────────────────────────────────────
_CHANROBLES_WATERMARKS = [
    r"chanroblesvirtualawlibrary",
    r"ChanRobles Virtual\s*[Ll]aw\s*Library",
    r"ChanRobles Virtual Law Library",
    r"ChanRobles On-Line Bar Review",
    r"ChanRobles MCLE On-line",
    r"ChanRobles Legal Resources[:\s]*",
    r"Jurisprudence,\s*Laws,\s*Statutes\s*&\s*Codes",
    r"Philippine Laws,\s*Statutes\s*&\s*Codes",
    r"Philippine Supreme Court Decisions",
    r"Significant Legal Resources",
    r"WorldWide Legal Re[sc]ources",
    r"US Federal Laws,\s*Statutes\s*&\s*Codes",
    r"US Supreme Court Decisions",
    r"The Business Page",
    r"ChanRobles Professional Review,\s*Inc\.",
]

# ── GoSupra branding ──────────────────────────────────────────────────────────
_GOSUPRA_WATERMARKS = [
    r"Supra Source",
    r"Toggle navigation",
    r"^Source$",
    r"^Documents$",
    r"^Jurisprudence$",
]


def _clean_lawphil(text: str) -> str:
    for pat in _LAWPHIL_WATERMARKS:
        text = re.sub(pat, "", text, flags=re.IGNORECASE)
    text = re.sub(r'\.(\s*)-(\s*)', r'. - ', text)
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    return text.strip()


def _clean_chanrobles(text: str) -> str:
    for pat in _CHANROBLES_WATERMARKS:
        text = re.sub(pat, "", text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r'\.(\s*)-(\s*)', r'. - ', text)
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    return text.strip()


def _clean_gosupra(text: str) -> str:
    for pat in _GOSUPRA_WATERMARKS:
        text = re.sub(pat, "", text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r'\.(\s*)-(\s*)', r'. - ', text)
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    return text.strip()


def _html_to_text(html_bytes: bytes) -> str:
    """
    Convert HTML to clean plain-text while preserving structure:
      - Each <p> is extracted with inline separator=" " so "SECTION 1. <em>Petition.</em>"
        stays on one line instead of splitting into two separate lines.
      - <ol> items get explicit letter markers (a. b. c.) because the original
        markers are CSS-generated and invisible to get_text().
      - <ul> items get a dash marker.
      - Consecutive list items within one <ol>/<ul> are joined with "\n" (single
        newline) so they form a compact block separated from surrounding paragraphs
        by double newlines.
    """
    soup = BeautifulSoup(html_bytes, "html.parser")
    for tag in soup(["script", "style", "head", "meta", "link",
                     "iframe", "nav", "footer", "header"]):
        tag.decompose()

    chunks: list[str] = []

    def _visit(node) -> None:
        """Recursively walk block-level elements, collecting text chunks."""
        if not hasattr(node, "name") or not node.name:
            return  # NavigableString or Comment at root level — skip
        if node.name == "ol":
            items = node.find_all("li", recursive=False)
            for idx, li in enumerate(items):
                letter = chr(ord("a") + idx)
                text = li.get_text(separator=" ").strip()
                if text:
                    # Each item is its own paragraph (\n\n) so ArticleNode splits
                    # it into a distinct segment for per-paragraph juris linking.
                    chunks.append(f"{letter}. {text}")
        elif node.name == "ul":
            items = node.find_all("li", recursive=False)
            for li in items:
                text = li.get_text(separator=" ").strip()
                if text:
                    chunks.append(f"- {text}")
        elif node.name == "p":
            text = node.get_text(separator=" ").strip()
            if text:
                chunks.append(text)
        else:
            # div, blockquote, table, body, etc. — recurse into children
            for child in node.children:
                _visit(child)

    root = soup.body if soup.body else soup
    for child in root.children:
        _visit(child)

    if chunks:
        return "\n\n".join(chunks)

    # Fallback: original flat approach
    lines = [ln.strip() for ln in soup.get_text(separator="\n").splitlines() if ln.strip()]
    return "\n\n".join(lines)


def _pdf_to_text(pdf_bytes: bytes) -> str:
    import pypdf
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    pages_text = []
    for page in reader.pages:
        t = page.extract_text() or ""
        if t.strip():
            pages_text.append(t)
    return "\n\n".join(pages_text)


def scrape_statute(statute: dict) -> tuple[bytes, str]:
    """Returns (raw_content_bytes, cleaned_md_text)."""
    src = statute["source"]
    url = statute["url"]

    if src == "pdf":
        resp = requests.get(url, headers={"User-Agent": _UA_BROWSER}, timeout=60)
        resp.raise_for_status()
        raw = resp.content
        text = _clean_lawphil(_pdf_to_text(raw))
        return raw, text

    if src == "gosupra":
        resp = requests.get(url, headers={"User-Agent": _UA_BOT}, timeout=30)
        resp.raise_for_status()
        raw = resp.content
        text = _clean_gosupra(_html_to_text(raw))
        return raw, text

    if src == "chanrobles":
        resp = requests.get(url, headers={"User-Agent": _UA_BROWSER}, timeout=30)
        resp.raise_for_status()
        raw = resp.content
        text = _clean_chanrobles(_html_to_text(raw))
        return raw, text

    # Default: lawphil / plain HTML
    resp = requests.get(url, headers={"User-Agent": _UA_BROWSER}, timeout=30)
    resp.raise_for_status()
    raw = resp.content
    text = _clean_lawphil(_html_to_text(raw))
    return raw, text


def main() -> None:
    HTML_DIR.mkdir(parents=True, exist_ok=True)
    MD_DIR.mkdir(parents=True, exist_ok=True)

    for statute in STATUTES:
        sid = statute["statute_id"]
        fn  = statute["filename"]
        src = statute["source"]
        ext = "pdf" if src == "pdf" else "html"

        md_path   = MD_DIR   / f"{fn}.md"
        raw_path  = HTML_DIR / f"{fn}.{ext}"

        print(f"\n[{sid}] {statute['label']}")

        if md_path.exists():
            print(f"  Already scraped — skipping")
            continue

        try:
            raw, cleaned = scrape_statute(statute)
            raw_path.write_bytes(raw)
            md_path.write_text(cleaned, encoding="utf-8")
            print(f"  Saved {len(cleaned):,} chars -> {md_path.name}")
        except Exception as e:
            print(f"  ERROR: {e}")

        time.sleep(1.5)

    print("\nDone. Check LexCode/Codals/md/remedial/ for output files.")


if __name__ == "__main__":
    main()
