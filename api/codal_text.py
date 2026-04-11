"""
Shared codal markdown normalization and LexPlay TTS flattening.

- normalize_storage_markdown: safe DB/source fixes (paragraph boundaries preserved:
  no merging/splitting of \\n\\n blocks beyond stripping empty lines from quote cleanup).
- tts_flatten_codal_body: single implementation for audio_provider + precache + diagnostics.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple


def fix_stray_quotation_artifacts(text: str) -> str:
    """
    Remove blockquote-export double quotes that often wrap amendatory paragraphs
    (parity with scripts/build_rpc_fidelity.load_all_amendments).
    Also drops lines that are only a stray quote character.
    """
    if not text:
        return text

    lines = text.split("\n")
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped in ('"', "'", "\u201c", "\u201d", "\u2018", "\u2019"):
            continue
        s = line
        s = re.sub(r'^\s*"\s*', "", s)
        s = re.sub(r'\s*"\s*$', "", s)
        s = re.sub(r"^\s*\u201c\s*", "", s)
        s = re.sub(r"\s*\u201d\s*$", "", s)
        out.append(s)
    text = "\n".join(out)

    # Orphan closing quote immediately after sentence end:  word."  or word." more
    text = re.sub(r'\.(\s*")(\s+[A-Za-z])', r".\2", text)
    text = re.sub(r'\.(\s*\u201d)(\s+[A-Za-z])', r".\2", text)

    return text


def normalize_storage_markdown(md: Optional[str]) -> str:
    """
    Apply once at ingest or batch repair. Keeps \\n\\n paragraph structure intact
    (does not inject enumeration line-breaks — those stay in ArticleNode for display).
    """
    if not md:
        return md or ""

    text = md.replace("\r\n", "\n").replace("\r", "\n")
    text = fix_stray_quotation_artifacts(text)

    # Un-escape markdown parenthesis markers \(1\) -> (1)
    text = re.sub(r"\\\(([^)]*)\\\)", r"(\1)", text)

    # Strip mistaken section headers that belong in section_label
    text = re.sub(r"^##\s+SECTION\s+\d+\s+.+$", "", text, flags=re.MULTILINE)

    # Strip leading H1 doc title (not Article/Section lines)
    text = re.sub(
        r"^#\s+(?!Article|Section|Art\.)[^\n]+\n?",
        "",
        text,
        count=1,
        flags=re.MULTILINE,
    )

    # Collapse 3+ newlines to double (preserve paragraph count, tidy spacing)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Amendment OCR / source glues :Provided,That without spaces
    text = re.sub(
        r":\s*Provided,\s*That(?=\s|[A-Za-z(])",
        ": Provided, That ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r":\s*Provided,\s*further,\s*That(?=\s|[A-Za-z(])",
        ": Provided, further, That ",
        text,
        flags=re.IGNORECASE,
    )

    return text.strip()


def tts_flatten_codal_body(content: str) -> str:
    """
    Turn codal markdown body into a single plain string suitable for TTS.
    Must stay aligned with historical LexPlay behavior (see audio_provider).
    """
    if not content:
        return ""
    clean = str(content).strip()
    clean = clean.replace("\r\n", "\n").replace("\r", "\n")

    # Strip a leading standalone source-reference number that some codals (Family Code,
    # Old Civil Code) prepend to the body — e.g. "5\nThe legal separation may be claimed…"
    # where 5 refers to the corresponding article in the prior law.
    # Only matches when the number is alone on its own opening line (no period/dash after it).
    clean = re.sub(r"^\s*\d{1,4}[a-zA-Z]?\s*\n", "", clean)

    clean = re.sub(r"[#*`_\[\]^]", " ", clean)
    # Semicolons terminate clauses (stronger than comma) → give TTS a full-stop prosody cue.
    # Colons introduce lists/continuations → soft pause is enough.
    clean = re.sub(r";", ". ", clean)
    clean = re.sub(r":", ", ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()

    clean = re.sub(r"\\[nrtfvb]", " ", clean)
    clean = clean.replace("\\", " ")
    clean = re.sub(r"\s+", " ", clean).strip()

    # Strip trailing source citations FIRST while parentheses are still intact.
    # Must run before the (N)→N, conversion below, which would destroy the parens
    # and prevent the tail stripper from recognising patterns like (1395) or (3a, Act No. 2710).
    clean = strip_codal_citation_tail(clean)

    # Convert inline parenthetical numbers like (1), (2), (3) → "1,", "2,", "3," for TTS.
    # strip_codal_citation_tail already removed trailing source citations before this point,
    # so remaining (N) patterns are list-item numbers or inline references — both read better as "N,".
    clean = re.sub(r"\(\s*(\d+)\s*\)", r"\1,", clean)
    clean = re.sub(r"\(\s*[₱P]\s*[\d,.]+\s*\)", "", clean)
    clean = re.sub(
        r"\s*\(\s*(?:(?:\d+[a-zA-Z]?|n|[A-Z]\d+)(?:\s*,\s*(?:\d+[a-zA-Z]?|n|[A-Z]\d+))*)\s*\)",
        " ",
        clean,
    )
    clean = re.sub(r"\s+", " ", clean).strip()

    # Strip the hard stop after 1-2-digit list-item numbers so TTS doesn't pause like a sentence end.
    # Matches only when preceded by a period or comma (i.e. inside a list, not at text start).
    # "to death, 1. If…"  →  "to death, 1, If…"
    # "three days. 2. If…" →  "three days. 2, If…"
    clean = re.sub(r"(?<=[.,]) (\d{1,2})\. (?=[A-Za-z])", r" \1, ", clean)

    return clean


def dedupe_codal_header_prefix(clean: str, header: Optional[str], clean_num: str) -> Tuple[Optional[str], str]:
    """
    If the flattened body already starts with the spoken header, omit the prefix
    (e.g. Article 266-A embedded in content).
    Also treat 'Art. 266-A' the same as 'Article 266-A' after flattening.
    """
    if not header:
        return header, clean
    cn = (clean_num or "").strip()
    header_bare = f"article {cn.lower()}"
    clean_header = header.lower().rstrip(".")
    cl = clean.lower().strip()
    if cl.startswith(header_bare) or cl.startswith(clean_header):
        return "", clean
    if cn and re.match(
        rf"^\s*(article|art\.)\s+{re.escape(cn.lower())}([\s.,;]|$)",
        cl,
    ):
        return "", clean
    return header, clean


# Canonical Art. 266 body (RA No. 10951, Sec. 61) — parity with src/frontend rpcArticle266Fallback.js
RPC_ARTICLE_266_BODY_MD = """The crime of slight physical injuries shall be punished:

1. By *arresto menor* when the offender has inflicted physical injuries which shall incapacitate the offended party for labor from one (1) days to nine (9) days, or shall require medical attendance during the same period.

2. By *arresto menor* or a fine not exceeding Forty thousand pesos (₱40,000) and censure when the offender has caused physical injuries which do not prevent the offended party from engaging in his habitual work nor require medical assistance.

3. By *arresto menor* in its minimum period or a fine not exceeding Five thousand pesos (₱5,000) when the offender shall ill-treat another by deed without causing any injury.
"""


def is_corrupted_rpc_article_266_body(md: Optional[str]) -> bool:
    """True when DB row for Art. 266 still holds 266-A / rape fragments (matches frontend heuristic)."""
    if not md or not isinstance(md, str):
        return False
    t = md.strip()
    if re.search(r"the crime of slight physical injuries", md, re.I):
        return False
    if re.search(r"As used in this Act,?\s*non-abusive shall mean", md, re.I):
        return True
    if re.search(r"carnal knowledge of another person", md, re.I):
        return True
    if re.match(r"^\s*1\)\s*By\s+a\s+person\s+who\s+shall\s+have\s+carnal\s+knowledge", t, re.I):
        return True
    if re.search(r"\bx\s+x\s+x\b", md, re.I) and re.search(r"\(16\)\s*years?\s+of\s+age", md, re.I):
        return True
    return False


def repair_rpc_article_266_for_tts(article_num: str, md: Optional[str]) -> str:
    """
    Apply the same recovery as ArticleNode.jsx: stale Art. 266 rows often open with a 266-A fragment.
    TTS reads raw content_md — without this, LexPlay speaks rape text for Art. 266.
    """
    if not md or str(article_num).strip() != "266":
        return md or ""
    text = md
    stripped = text.lstrip()
    if re.match(r'^"?\s*Article\s+266-A\.', stripped, re.I):
        phrase = "the crime of slight physical injuries"
        ix = text.lower().find(phrase)
        if ix != -1:
            text = text[ix:].lstrip()
        else:
            for _ in range(25):
                if not re.match(r'^"?\s*Article\s+266-A\.', text.lstrip(), re.I):
                    break
                text = re.sub(r"^[^\n]*(?:\n|$)", "", text, count=1).lstrip()
    if is_corrupted_rpc_article_266_body(text):
        text = RPC_ARTICLE_266_BODY_MD
    return text


def raw_markdown_opens_with_article_line(content: str, article_num_key: str) -> bool:
    """
    True if raw content_md opens with Article N / Art. N (including **Article** markdown).
    Used so we omit the spoken article line when the body already embeds it (e.g. 266-A).
    """
    if not content or not (article_num_key or "").strip():
        return False
    key = re.sub(r"[\u2010-\u2015\u2212]", "-", article_num_key.strip())
    esc = re.escape(key)
    head = content.strip()
    para = re.split(r"\n\s*\n", head, maxsplit=1)[0]
    first_line = (para.split("\n", 1)[0] if para else "")[:500]
    probe = re.sub(r"\*+", "", first_line)
    probe = probe.strip().lstrip("\"'").strip()
    probe = re.sub(r"^#+\s*", "", probe)
    if re.match(rf"(?is)^(Article|Art\.)\s+{esc}(\.|,|\s|;|$)", probe):
        return True
    compact = re.sub(r"\s+", " ", head[:800]).strip().lower()
    k = key.lower()
    return compact.startswith(f"article {k}") or compact.startswith(f"art. {k}")


def _compact_lower(s: str, max_len: int = 600) -> str:
    t = re.sub(r"[#*`_\[\]]", " ", (s or "").strip())
    return re.sub(r"\s+", " ", t).strip().lower()[:max_len]


def _section_label_title_tail(section_label: str) -> str:
    """Text after 'Section I' / 'Section 1' (topic only), for matching body headings."""
    sl = (section_label or "").strip()
    if not sl:
        return ""
    rest = re.sub(
        r"(?i)^\.?\s*section\s+[ivxlcdm\d]+\s*",
        "",
        sl,
    ).strip()
    rest = re.sub(r"^[\.\-–—:\s]+", "", rest)
    return rest.lower()


def _is_rpc_266_subarticle(article_num: Optional[str]) -> bool:
    if not article_num:
        return False
    s = re.sub(r"\s+", "", str(article_num).strip().upper())
    return s in (
        "266A",
        "266-A",
        "266B",
        "266-B",
        "266C",
        "266-C",
        "266D",
        "266-D",
    )


def _looks_like_section_heading_line(snippet: str) -> bool:
    """Standalone SECTION line (markdown or plain), without requiring DB section_label match."""
    t = (snippet or "").strip()
    if not t:
        return False
    if re.match(r"(?is)^(?:[#*\s\"'’]*)(#{0,6}\s*)?(section|sec\.)\b", t):
        return True
    if re.match(r'(?i)^"?\s*section\s+[ivxlcdm\d]', t):
        return True
    if re.match(r"(?i)^section\s+[ivxlcdm\d]+", t):
        return True
    return False


def _opening_snippet_matches_section(snippet: str, section_label: str) -> bool:
    """True when this opening text (first block or single line) is the same SECTION as section_label."""
    sl = (section_label or "").strip()
    if len(sl) < 4:
        return False
    sl_c = re.sub(r"\s+", " ", sl.lower()).strip()
    first_para = (snippet or "").strip()
    if not first_para:
        return False
    early = _compact_lower(first_para, 520)

    topic = _section_label_title_tail(sl)
    topic_ok = len(topic) >= 3

    if re.match(r"(?is)^(?:[#*\s\"'’]*)(#{1,6}\s*)?section\s+", first_para):
        if len(sl_c) >= 10 and sl_c[:100] in early[:400]:
            return True
        if topic_ok and topic in early[:350]:
            return True

    if re.match(r"^\s*\"?\s*section\s+[ivxlcdm\d]+", first_para.strip(), re.I):
        if len(sl_c) >= 10 and (sl_c[:100] in early[:320] or early.startswith(sl_c[:min(50, len(sl_c))])):
            return True
        if topic_ok and topic in early[:320]:
            return True

    key = sl_c[: min(120, len(sl_c))]
    if len(key) >= 12:
        pos = early.find(key[:80])
        if pos >= 0 and pos < 100:
            return True
        if early.startswith(key[: min(40, len(key))]):
            return True

    return False


def body_embeds_rpc_section(content: str, clean: str, section_label: str) -> bool:
    """
    True when content already opens with this SECTION (markdown ## SECTION … or plain
    'Section I …'), so LexPlay should not repeat section_label after Title/Chapter.
    Covers 266-A–D and similar rows where the section line is duplicated in content_md.
    """
    raw = (content or "").strip()
    if raw:
        first_para = re.split(r"\n\s*\n", raw, maxsplit=1)[0]
        if _opening_snippet_matches_section(first_para, section_label):
            return True

    cl = _compact_lower(clean or "", 450)
    sl = (section_label or "").strip()
    if len(sl) < 4:
        return False
    sl_c = re.sub(r"\s+", " ", sl.lower()).strip()
    topic = _section_label_title_tail(sl)
    topic_ok = len(topic) >= 3
    if re.match(r"^\s*section\s+[ivxlcdm\d]+", cl):
        if topic_ok and topic in cl[:280]:
            return True
        if len(sl_c) >= 10 and sl_c[:90] in cl[:240]:
            return True

    return False


def tts_strip_leading_embedded_section(
    content_md: str,
    section_label: Optional[str],
    article_num: Optional[str] = None,
) -> str:
    """
    Remove a leading SECTION heading from content_md when it duplicates section_label,
    so TTS never speaks it twice (same effect as cleaning the DB for LexPlay only).
    Handles a paragraph block and/or standalone markdown SECTION lines before Article.
    For Art. 266-A–D, also strips any leading SECTION line even when labels mismatch the DB.
    """
    sl = (section_label or "").strip()
    relaxed = _is_rpc_266_subarticle(article_num)
    if not content_md:
        return content_md or ""
    if len(sl) < 4 and not relaxed:
        return content_md or ""

    text = content_md.replace("\r\n", "\n").replace("\r", "\n")
    out = text.strip()

    def _block_matches_section(block: str) -> bool:
        if len(sl) >= 4 and _opening_snippet_matches_section(block, sl):
            return True
        return relaxed and _looks_like_section_heading_line(block)

    parts = re.split(r"\n\s*\n", out, maxsplit=1)
    if len(parts) == 2 and _block_matches_section(parts[0]):
        out = parts[1].strip()

    lines = out.split("\n")
    max_passes = 8
    for _ in range(max_passes):
        if not lines:
            break
        while lines and not lines[0].strip():
            lines.pop(0)
        if not lines:
            break
        top = lines[0].strip()
        if not (
            re.match(r"(?is)^#{0,6}\s*section\s+", top)
            or re.match(r'(?i)^"?\s*section\s+[ivxlcdm\d]', top)
            or (relaxed and re.match(r"(?i)^section\s+[ivxlcdm\d]+", top))
        ):
            break
        if len(sl) >= 4 and _opening_snippet_matches_section(top, sl):
            lines.pop(0)
            continue
        if relaxed and _looks_like_section_heading_line(top):
            lines.pop(0)
            continue
        break

    return "\n".join(lines).strip()


def tts_strip_leading_embedded_title(content_md: str, title_label: Optional[str]) -> str:
    """
    Remove a first paragraph that repeats title_label (common when chapters paste TITLE … in body).
    """
    tl = (title_label or "").strip()
    if not content_md or len(tl) < 20:
        return content_md or ""

    text = content_md.replace("\r\n", "\n").replace("\r", "\n").strip()
    parts = re.split(r"\n\s*\n", text, maxsplit=1)
    if len(parts) != 2:
        return content_md or ""

    first = parts[0].strip()
    early = _compact_lower(first, min(len(tl) + 120, 500))
    tk = re.sub(r"\s+", " ", tl.lower()).strip()
    if len(tk) < 20:
        return content_md or ""

    prefix = tk[: min(72, len(tk))]

    # A genuine embedded structural title header is short — roughly the title label itself
    # plus a small prefix like "TITLE VI - " (≤ 20 extra chars).
    # If first paragraph is much longer, it is prose content, not a header, and must NOT be stripped.
    if len(first) > len(tl) + 25:
        return content_md or ""

    if early.startswith(prefix):
        return parts[1].strip()

    # Second condition: title keywords appear early but are preceded by a structural keyword
    # (e.g. "TITLE VI - Property..." or "## Property..."), NOT natural prose like "The property...".
    pos = early.find(prefix)
    if 0 < pos < 80 and prefix in early[:140]:
        pre_text = early[:pos].strip()
        if re.match(
            r"^(?:title|chapter|sec(?:tion)?|book|[ivxlcdm]+\s*[\-—.:\s]|#+|\d+[\-—.:\s])",
            pre_text,
            re.IGNORECASE,
        ):
            return parts[1].strip()

    return content_md or ""


def body_starts_with_article_identifier(
    clean: str,
    clean_num: str,
    art_title: Optional[str] = None,
) -> bool:
    """
    True if flattened TTS body already opens with this article (Article/Art. + number),
    optionally with the short title after a period.
    Used to omit only the spoken article line while keeping Book/Title/Section prefixes.
    """
    cn = (clean_num or "").strip().lower()
    if not cn:
        return False
    cl = clean.lower().strip()
    if re.match(rf"^\s*(article|art\.)\s+{re.escape(cn)}([\s.,;]|$)", cl):
        return True
    if art_title and len(art_title.strip()) > 3:
        t = art_title.strip()
        if re.match(
            rf"^\s*(article|art\.)\s+{re.escape(cn)}\.\s*{re.escape(t)}",
            cl,
            flags=re.IGNORECASE,
        ):
            return True
    return False


# ---------------------------------------------------------------------------
# Structural-label helpers
# ---------------------------------------------------------------------------

_ROMAN_TO_ARABIC: dict[str, int] = {
    "i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5,
    "vi": 6, "vii": 7, "viii": 8, "ix": 9, "x": 10,
    "xi": 11, "xii": 12, "xiii": 13, "xiv": 14, "xv": 15,
    "xvi": 16, "xvii": 17, "xviii": 18, "xix": 19, "xx": 20,
}

_WORD_TO_ARABIC: dict[str, int] = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "preliminary": 0,
}

# Pattern for trailing parenthetical source/amendment citations
_CITATION_TAIL_RE = re.compile(
    r"\s*\(\s*(?:"
    r"\d+[a-zA-Z]?"          # (1a), (5), (1156)
    r"|n"                    # (n)
    r"|[Aa]s\s+amended.*"    # (As amended by ...)
    r"|[Cc]f\."              # (Cf. Art. ...)
    r"|[Aa]rts?\.\s*[\d(]"  # (Art. 1...), (Arts. 1-10)
    r"|[Ss]ecs?\.\s*[\d(]"  # (Sec. 1...)
    r"|[Rr]\.?\s*[Aa]\.?\s*\d"   # (R.A. 386)
    r"|[Pp]\.?\s*[Dd]\.?\s*\d"   # (P.D. 1445)
    r")[^)]*\)\s*$",
    re.DOTALL,
)


def strip_codal_citation_tail(text: str) -> str:
    """
    Strip trailing source/amendment citation annotations from codal titles and labels.
    Handles: (n), (1a), (1156), (As amended by R.A. 6809), (Art. 1, CC), (Arts. 1-10), etc.
    Applies up to 3 times to remove stacked annotations.
    """
    if not text:
        return text
    for _ in range(3):
        m = _CITATION_TAIL_RE.search(text.rstrip())
        if m:
            text = text[: m.start()]
        else:
            break
    return text.strip()


def tts_format_structural_label(label: str, num, level_name: str) -> str:
    """
    Build a TTS-friendly structural header like "Title 9. Crimes Against Persons"
    or "Chapter 1. Effect And Application Of Laws".

    Strips any embedded "TITLE IX —", "CHAPTER ONE:" style prefix from the label,
    then rebuilds as "Level N. Description" using an Arabic numeral so the neural
    TTS model reads it unambiguously.

    Works for:
      - RPC labels that embed the prefix: "TITLE IX - CRIMES AGAINST PERSONS"
      - CIV/LABOR labels without prefix: "Crimes Against Persons" + num=9
    """
    label = strip_codal_citation_tail((label or "").strip())
    if not label and num is None:
        return ""

    # Attempt to strip an embedded "LEVEL_NAME (N|ROMAN|WORD) [-:—.] " prefix
    prefix_pat = re.compile(
        r"^" + re.escape(level_name) + r"\s+"
        r"([IVX]+|\d+|ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN"
        r"|ELEVEN|TWELVE|THIRTEEN|FOURTEEN|FIFTEEN|SIXTEEN|SEVENTEEN|EIGHTEEN)"
        r"\s*[-:—.]\s*",
        re.IGNORECASE,
    )
    m = prefix_pat.match(label)
    description: str = label
    extracted_num: Optional[int] = None

    if m:
        raw = m.group(1).lower()
        description = label[m.end():].strip()
        if raw.isdigit():
            extracted_num = int(raw)
        elif raw in _ROMAN_TO_ARABIC:
            extracted_num = _ROMAN_TO_ARABIC[raw]
        elif raw in _WORD_TO_ARABIC:
            extracted_num = _WORD_TO_ARABIC[raw]

    final_num: Optional[int] = extracted_num
    if final_num is None and num is not None:
        try:
            final_num = int(num)
        except (TypeError, ValueError):
            pass

    desc = strip_codal_citation_tail(description).title() if description else ""

    if final_num is not None:
        return f"{level_name} {final_num}. {desc}" if desc else f"{level_name} {final_num}"
    # No number available — just use the (possibly cleaned) label
    return desc or label.title()


def _arabic_to_roman(num: int) -> str:
    if num <= 0:
        return str(num)
    pairs = (
        (1000, "M"),
        (900, "CM"),
        (500, "D"),
        (400, "CD"),
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    )
    n = num
    parts: list[str] = []
    for v, sym in pairs:
        while n >= v:
            parts.append(sym)
            n -= v
    return "".join(parts)


def tts_book_heading_line(row: dict, book_prefix: str = "Book") -> Optional[str]:
    """
    Match LexCodeStream: Book N — subtitle when book_label is present and does not
    already start with \"Book\"; skip labels that are PRELIMINARY-only book stubs.
    Uses Arabic numerals (Book 1, Book 2) for unambiguous TTS pronunciation.
    """
    book = row.get("book")
    bl = strip_codal_citation_tail((row.get("book_label") or "").strip())
    book_int: Optional[int] = None
    if book is not None and str(book).strip() != "":
        try:
            book_int = int(book)
        except (TypeError, ValueError):
            pass
    if bl:
        if "preliminary" in bl.lower():
            return None
        # If book_label already embeds "Book N", strip it and rebuild with Arabic numeral
        m = re.match(r"(?i)^book\s+([IVX]+|\d+)\s*[-—.]?\s*(.*)", bl)
        if m:
            embedded_raw = m.group(1).lower()
            rest = m.group(2).strip()
            try:
                embedded_int = (
                    int(embedded_raw) if embedded_raw.isdigit()
                    else _ROMAN_TO_ARABIC.get(embedded_raw)
                )
            except (TypeError, ValueError):
                embedded_int = None
            use_num = embedded_int or book_int
            if use_num is not None:
                return f"{book_prefix} {use_num}. {rest.title()}" if rest else f"{book_prefix} {use_num}"
            return bl.title()
        if book_int is not None:
            return f"{book_prefix} {book_int}. {bl.title()}"
        return bl.title()
    if book_int is not None:
        return f"{book_prefix} {book_int}"
    return None
