"""
Provision Scraper for Bar 2026 Reviewer
========================================
Priority:
  1. LawPhil.net  — best quality; strip branding HTML
  2. SC eLibrary  — for Republic Acts not found on LawPhil
  3. Official Gazette — HTML pages only (skip PDFs, poor OCR)
  4. Search-grounded Gemini — fallback; returns text + citation URL

Usage (standalone):
    python tools/provision_scraper.py --url https://lawphil.net/...
    python tools/provision_scraper.py --ra 9165 --sections "Sec. 5,11,21"
"""

import re
import time
import logging
import argparse
import urllib.request
import urllib.error
from typing import Optional

log = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

LAWPHIL_BASE = "https://lawphil.net"
ELIB_RA_BASE = "https://elibrary.judiciary.gov.ph/republic_acts"
OG_BASE      = "https://www.officialgazette.gov.ph"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

REQUEST_DELAY = 1.5   # seconds between requests (be polite)
MAX_RETRIES   = 2


# ── Core fetch ─────────────────────────────────────────────────────────────────

def _fetch_html(url: str) -> Optional[str]:
    """Fetch raw HTML from URL. Returns None on error."""
    for attempt in range(MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as resp:
                content_type = resp.headers.get("Content-Type", "")
                # Reject PDF responses early
                if "pdf" in content_type.lower():
                    log.warning(f"PDF detected at {url} — skipping")
                    return None
                raw = resp.read()
                # Detect PDF by magic bytes even if content-type is wrong
                if raw[:4] == b"%PDF":
                    log.warning(f"PDF magic bytes at {url} — skipping")
                    return None
                # Try UTF-8, fall back to latin-1
                try:
                    return raw.decode("utf-8")
                except UnicodeDecodeError:
                    return raw.decode("latin-1", errors="replace")
        except urllib.error.HTTPError as e:
            log.warning(f"HTTP {e.code} for {url} (attempt {attempt + 1})")
            if e.code in (403, 404):
                return None
        except Exception as e:
            log.warning(f"Fetch error for {url}: {e} (attempt {attempt + 1})")
        if attempt < MAX_RETRIES:
            time.sleep(REQUEST_DELAY * (attempt + 1))
    return None


# ── HTML → clean text ──────────────────────────────────────────────────────────

def _strip_lawphil_html(html: str) -> str:
    """
    Strip LawPhil branding, navigation, ads.
    LawPhil wraps legal text in <div class="entry-content"> or similar.
    We aggressively remove noise and extract meaningful text.
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        # Fallback: naive regex strip if bs4 not installed
        return _regex_strip(html)

    soup = BeautifulSoup(html, "html.parser")

    # Remove noise elements
    for tag in soup.find_all(["script", "style", "nav", "header", "footer",
                               "aside", "form", "noscript", "iframe",
                               "button", "input", "select"]):
        tag.decompose()

    # Remove by class/id patterns common to LawPhil branding
    noise_patterns = [
        "breadcrumb", "widget", "sidebar", "menu", "banner",
        "advertisement", "related", "social", "share", "comment",
        "footer", "header", "navbar", "topbar", "copyright",
        "site-info", "site-branding", "site-title",
    ]
    for pattern in noise_patterns:
        for el in soup.find_all(True, {"class": lambda c: c and any(p in " ".join(c).lower() for p in noise_patterns)}):
            el.decompose()

    # Try to find the main content container
    content = (
        soup.find("div", class_=re.compile(r"entry.content|post.content|article.body|main.content|content.area|body.text", re.I))
        or soup.find("article")
        or soup.find("main")
        or soup.find("div", id=re.compile(r"content|main|primary", re.I))
        or soup.body
    )

    if not content:
        return _regex_strip(html)

    # Extract text, preserve paragraph breaks
    lines = []
    for element in content.descendants:
        if element.name in ("p", "br", "h1", "h2", "h3", "h4", "li", "tr"):
            lines.append("\n")
        if hasattr(element, "string") and element.string:
            text = element.string.strip()
            if text:
                lines.append(text)

    raw_text = " ".join(lines)
    return _clean_text(raw_text)


def _strip_elib_html(html: str) -> str:
    """Strip SC eLibrary chrome and extract statute text."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup.find_all(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        content = (
            soup.find("div", class_=re.compile(r"content|body|statute|document", re.I))
            or soup.find("main")
            or soup.body
        )
        return _clean_text(content.get_text(separator="\n") if content else "")
    except Exception:
        return _regex_strip(html)


def _regex_strip(html: str) -> str:
    """Naive regex-based HTML strip — fallback when bs4 is unavailable."""
    # Remove script/style blocks
    html = re.sub(r"<(script|style)[^>]*>.*?</(script|style)>", " ", html, flags=re.S | re.I)
    # Remove HTML tags
    html = re.sub(r"<[^>]+>", " ", html)
    return _clean_text(html)


def _clean_text(text: str) -> str:
    """Normalize whitespace and remove junk characters."""
    # Collapse repeated whitespace / newlines
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove common LawPhil boilerplate phrases
    boilerplate = [
        r"lawphil\.net.*?(?=\n)",
        r"THE LAWPHIL PROJECT.*?(?=\n)",
        r"Arellano Law Foundation.*?(?=\n)",
        r"Back to Main.*?(?=\n)",
        r"Republic of the Philippines.*?All Rights Reserved.*?(?=\n)",
    ]
    for pattern in boilerplate:
        text = re.sub(pattern, "", text, flags=re.I)
    return text.strip()


# ── Section extraction ─────────────────────────────────────────────────────────

def extract_sections(full_text: str, sections_spec: Optional[str]) -> str:
    """
    Given the full text of a statute and a sections_spec like 'Secs. 4, 5, 21',
    extract only those sections. Falls back to returning the full text if
    extraction is ambiguous.
    """
    if not sections_spec:
        return full_text

    # Parse section numbers from spec
    nums = re.findall(r"\d+(?:\([a-z0-9]+\))*", sections_spec.lower())
    if not nums:
        return full_text

    # Try to split the full text by section markers
    section_pattern = re.compile(
        r"((?:SECTION|SEC\.|Sec\.)\s*\d+[A-Za-z]?(?:\s*\([^)]+\))*\.?)",
        re.IGNORECASE
    )
    parts = section_pattern.split(full_text)

    if len(parts) <= 1:
        # Statute not well-structured for extraction — return all
        return full_text

    collected = []
    i = 1
    while i < len(parts) - 1:
        header = parts[i]
        body   = parts[i + 1] if i + 1 < len(parts) else ""
        # Check if this section's number is in our target list
        header_nums = re.findall(r"\d+", header)
        if any(n in nums for n in header_nums):
            collected.append(header.strip() + " " + body.strip())
        i += 2

    if collected:
        return "\n\n".join(collected)
    return full_text   # fallback


# ── Source-specific scrapers ───────────────────────────────────────────────────

def scrape_lawphil(url: str, sections_spec: Optional[str] = None) -> dict:
    """Scrape a provision from LawPhil. Returns {text, source_url, source_type}."""
    time.sleep(REQUEST_DELAY)
    html = _fetch_html(url)
    if not html:
        return {"text": None, "source_url": url, "source_type": "lawphil", "error": "fetch_failed"}

    text = _strip_lawphil_html(html)
    if sections_spec:
        text = extract_sections(text, sections_spec)

    if len(text) < 100:
        return {"text": None, "source_url": url, "source_type": "lawphil", "error": "content_too_short"}

    return {"text": text, "source_url": url, "source_type": "lawphil"}


def scrape_elib(ra_number: str, sections_spec: Optional[str] = None) -> dict:
    """Scrape a Republic Act from SC eLibrary."""
    url = f"{ELIB_RA_BASE}/{ra_number}"
    time.sleep(REQUEST_DELAY)
    html = _fetch_html(url)
    if not html:
        return {"text": None, "source_url": url, "source_type": "elib", "error": "fetch_failed"}

    text = _strip_elib_html(html)
    if sections_spec:
        text = extract_sections(text, sections_spec)

    if len(text) < 100:
        return {"text": None, "source_url": url, "source_type": "elib", "error": "content_too_short"}

    return {"text": text, "source_url": url, "source_type": "elib"}


def scrape_official_gazette(url: str, sections_spec: Optional[str] = None) -> dict:
    """Scrape from Official Gazette — HTML pages only. Returns None if PDF."""
    time.sleep(REQUEST_DELAY)
    html = _fetch_html(url)
    if not html:
        return {"text": None, "source_url": url, "source_type": "og", "error": "fetch_failed_or_pdf"}

    # Strip OG navigation/chrome (similar approach to LawPhil)
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup.find_all(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        content = soup.find("div", class_=re.compile(r"entry|content|post", re.I)) or soup.body
        text = _clean_text(content.get_text(separator="\n") if content else "")
    except Exception:
        text = _regex_strip(html)

    if sections_spec:
        text = extract_sections(text, sections_spec)

    if len(text) < 100:
        return {"text": None, "source_url": url, "source_type": "og", "error": "content_too_short"}

    return {"text": text, "source_url": url, "source_type": "og"}


# ── Main retrieval with fallback chain ────────────────────────────────────────

def retrieve_provision(provision: dict) -> dict:
    """
    Main entry point. Given a provision dict from the topic map, retrieve its
    text using the priority chain: LawPhil → SC eLib → OG → AI fallback marker.

    Returns the provision dict augmented with:
      retrieved_text, retrieved_source_url, retrieved_source_type, retrieval_error
    """
    source = provision.get("source", "scrape")

    # DB provisions — caller handles these separately via SQL
    if source == "db":
        return {**provision, "retrieval_status": "db"}

    # Case references — handled via sc_decided_cases table
    if source == "db_case":
        return {**provision, "retrieval_status": "db_case"}

    scrape_url      = provision.get("scrape_url", "")
    sections_spec   = provision.get("specific_sections")

    # ── 1. LawPhil (primary) ──────────────────────────────────────────────────
    if scrape_url and "lawphil" in scrape_url:
        result = scrape_lawphil(scrape_url, sections_spec)
        if result.get("text"):
            log.info(f"  ✓ LawPhil: {provision['label'][:60]}")
            return {**provision, **result, "retrieval_status": "ok"}

        # LawPhil failed — try SC eLib for Republic Acts
        statute_id = provision.get("statute_id", "")
        ra_match = re.match(r"RA-(\d+)", statute_id)
        if ra_match:
            ra_num = ra_match.group(1)
            log.info(f"  → LawPhil failed, trying SC eLib for RA {ra_num}")
            result = scrape_elib(ra_num, sections_spec)
            if result.get("text"):
                log.info(f"  ✓ SC eLib: {provision['label'][:60]}")
                return {**provision, **result, "retrieval_status": "ok"}

    # ── 2. SC eLib direct (if no lawphil URL) ────────────────────────────────
    statute_id = provision.get("statute_id", "")
    ra_match = re.match(r"RA-(\d+)", statute_id)
    if ra_match and not scrape_url:
        ra_num = ra_match.group(1)
        result = scrape_elib(ra_num, sections_spec)
        if result.get("text"):
            log.info(f"  ✓ SC eLib: {provision['label'][:60]}")
            return {**provision, **result, "retrieval_status": "ok"}

    # ── 3. Mark as needing AI fallback ───────────────────────────────────────
    log.warning(f"  ✗ All sources failed: {provision['label'][:60]} — flagged for AI fallback")
    return {
        **provision,
        "text": None,
        "source_url": scrape_url,
        "source_type": "failed",
        "retrieval_status": "ai_fallback",
    }


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description="Scrape a legal provision")
    parser.add_argument("--url", help="Direct URL to scrape")
    parser.add_argument("--ra",  help="Republic Act number (uses eLib)")
    parser.add_argument("--sections", help="Sections to extract, e.g. 'Sec. 4, 5'")
    args = parser.parse_args()

    if args.url:
        result = scrape_lawphil(args.url, args.sections)
    elif args.ra:
        result = scrape_elib(args.ra, args.sections)
    else:
        parser.print_help()
        exit(1)

    if result.get("text"):
        print(f"\n[Source: {result['source_url']}]\n")
        print(result["text"][:3000])
        print(f"\n... ({len(result['text'])} chars total)")
    else:
        print(f"Failed: {result.get('error')}")
