"""
Legal document section parser for RAG chunking.

Identifies and extracts named sections from formatted case/statute text
so the RAG Engine receives well-structured, legally-coherent chunks.

Sections are ranked by retrieval priority:
  1. MAIN DOCTRINE / RATIO DECIDENDI  (highest — core legal rule)
  2. RULING / ISSUES                  (high — court's holding)
  3. CASE METADATA / PROVISION TEXT   (high — identity + text)
  4. FACTS / SIGNIFICANCE             (medium — context)
  5. FULL TEXT                        (base — complete source)
"""

import re
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional


class SectionPriority(IntEnum):
    CRITICAL  = 5   # doctrine, ratio — always retrieved first
    HIGH      = 4   # ruling, issues, provision text
    MEDIUM    = 3   # facts, significance, metadata
    LOW       = 2   # full text body
    MINIMAL   = 1   # obiter, footnotes


# Map section header → priority
SECTION_PRIORITY_MAP: dict[str, SectionPriority] = {
    "MAIN DOCTRINE":       SectionPriority.CRITICAL,
    "RATIO DECIDENDI":     SectionPriority.CRITICAL,
    "ELEMENTS":            SectionPriority.CRITICAL,
    "ELEMENTS / REQUISITES": SectionPriority.CRITICAL,
    "RULING":              SectionPriority.HIGH,
    "ISSUES":              SectionPriority.HIGH,
    "PROVISION TEXT":      SectionPriority.HIGH,
    "PROVISION METADATA":  SectionPriority.HIGH,
    "LEGAL CONCEPT":       SectionPriority.HIGH,
    "DEFINITION":          SectionPriority.HIGH,
    "CASE METADATA":       SectionPriority.MEDIUM,
    "FACTS":               SectionPriority.MEDIUM,
    "SIGNIFICANCE":        SectionPriority.MEDIUM,
    "SOURCES":             SectionPriority.MEDIUM,
    "FULL TEXT":           SectionPriority.LOW,
    "OBITER":              SectionPriority.MINIMAL,
    "DISSENT":             SectionPriority.MINIMAL,
    "CONCURRENCE":         SectionPriority.MINIMAL,
}

# Regex to detect section headers in our formatted documents
SECTION_HEADER_RE = re.compile(
    r"^===\s+(.+?)\s+===\s*$",
    re.MULTILINE
)

# Legal section keywords for detecting sections in raw full text
# (used when the document is not pre-formatted — e.g. raw SC decisions)
RAW_SECTION_PATTERNS = [
    (re.compile(r"^\s*(FACTS?|STATEMENT OF (THE )?FACTS?)\s*:?\s*$", re.I | re.M), "FACTS"),
    (re.compile(r"^\s*(ISSUE[S]?|QUESTION[S]? (PRESENTED|RAISED)?)\s*:?\s*$", re.I | re.M), "ISSUES"),
    (re.compile(r"^\s*(RULING|HELD?|DECISION|COURT.S RULING)\s*:?\s*$", re.I | re.M), "RULING"),
    (re.compile(r"^\s*(RATIO DECIDENDI|RATIO|RATIONALE)\s*:?\s*$", re.I | re.M), "RATIO DECIDENDI"),
    (re.compile(r"^\s*(DISPOSITIVE (PORTION|PART)|WHEREFORE)\s*:?\s*$", re.I | re.M), "DISPOSITION"),
    (re.compile(r"^\s*(OBITER DICTUM|OBITER)\s*:?\s*$", re.I | re.M), "OBITER"),
    (re.compile(r"^\s*(DISSENTING OPINION|DISSENT)\s*:?\s*$", re.I | re.M), "DISSENT"),
]


@dataclass
class DocumentSection:
    name: str
    content: str
    priority: SectionPriority
    char_start: int
    char_end: int
    word_count: int = field(init=False)

    def __post_init__(self):
        self.word_count = len(self.content.split())

    @property
    def is_empty(self) -> bool:
        return len(self.content.strip()) < 10

    def to_chunk_metadata(self) -> dict:
        return {
            "section":    self.name,
            "priority":   int(self.priority),
            "word_count": self.word_count,
        }


@dataclass
class ParsedDocument:
    doc_type: str                          # "case" | "provision" | "flashcard"
    sections: list[DocumentSection]
    raw_text: str
    metadata: dict = field(default_factory=dict)

    @property
    def doctrine_section(self) -> Optional[DocumentSection]:
        for s in self.sections:
            if s.priority == SectionPriority.CRITICAL and not s.is_empty:
                return s
        return None

    @property
    def high_priority_sections(self) -> list[DocumentSection]:
        return [s for s in self.sections
                if s.priority >= SectionPriority.HIGH and not s.is_empty]

    @property
    def total_words(self) -> int:
        return sum(s.word_count for s in self.sections)

    def get_retrieval_context(self, max_words: int = 4000) -> str:
        """
        Build a retrieval-optimised string: doctrine first, then ruling,
        then other sections up to max_words. Used when loading context
        for Gemini generation.
        """
        parts = []
        budget = max_words

        # Always include critical sections first
        for section in sorted(self.sections,
                               key=lambda s: (s.priority, -s.word_count),
                               reverse=True):
            if section.is_empty:
                continue
            words = section.content.split()
            if len(words) <= budget:
                parts.append(f"[{section.name}]\n{section.content}")
                budget -= len(words)
            elif budget > 100:
                # Include truncated version
                truncated = " ".join(words[:budget])
                parts.append(f"[{section.name}]\n{truncated}... [truncated]")
                budget = 0
            if budget <= 0:
                break

        return "\n\n".join(parts)


# ── Parser ─────────────────────────────────────────────────────────────────────

def parse_document(text: str) -> ParsedDocument:
    """
    Parse a pre-formatted legal document (from export.py format) into sections.
    Detects === SECTION NAME === headers and splits accordingly.
    """
    if not text or not text.strip():
        return ParsedDocument(doc_type="unknown", sections=[], raw_text=text or "")

    # Detect doc type from first meaningful section
    doc_type = _detect_doc_type(text)

    # Find all section headers and their positions
    headers = [(m.group(1).strip(), m.start(), m.end())
               for m in SECTION_HEADER_RE.finditer(text)]

    if not headers:
        # No structured headers — parse raw full text
        return _parse_raw(text, doc_type)

    sections = []
    for i, (name, hdr_start, hdr_end) in enumerate(headers):
        content_start = hdr_end
        content_end   = headers[i + 1][1] if i + 1 < len(headers) else len(text)
        content       = text[content_start:content_end].strip()

        priority = SECTION_PRIORITY_MAP.get(name, SectionPriority.LOW)
        sections.append(DocumentSection(
            name=name,
            content=content,
            priority=priority,
            char_start=hdr_start,
            char_end=content_end,
        ))

    # Extract metadata from CASE METADATA / PROVISION METADATA section
    metadata = _extract_metadata(sections)

    return ParsedDocument(
        doc_type=doc_type,
        sections=[s for s in sections if not s.is_empty],
        raw_text=text,
        metadata=metadata,
    )


def _detect_doc_type(text: str) -> str:
    first_500 = text[:500].upper()
    if "CASE METADATA" in first_500:
        return "case"
    if "PROVISION METADATA" in first_500:
        return "provision"
    if "LEGAL CONCEPT" in first_500:
        return "flashcard"
    return "unknown"


def _extract_metadata(sections: list[DocumentSection]) -> dict:
    """Parse key:value pairs from the metadata section."""
    meta = {}
    for section in sections:
        if "METADATA" not in section.name:
            continue
        for line in section.content.splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                meta[key.strip().lower().replace(" ", "_")] = val.strip()
    return meta


def _parse_raw(text: str, doc_type: str) -> ParsedDocument:
    """
    Fallback: detect sections in raw SC decision text using keyword patterns.
    Used when full_text_md doesn't follow our structured format.
    """
    # Find pattern matches sorted by position
    matches = []
    for pattern, section_name in RAW_SECTION_PATTERNS:
        for m in pattern.finditer(text):
            matches.append((m.start(), section_name, m.end()))
    matches.sort(key=lambda x: x[0])

    if not matches:
        # No sections found — return as single full-text section
        return ParsedDocument(
            doc_type=doc_type,
            sections=[DocumentSection(
                name="FULL TEXT",
                content=text.strip(),
                priority=SectionPriority.LOW,
                char_start=0,
                char_end=len(text),
            )],
            raw_text=text,
        )

    sections = []
    for i, (start, name, end) in enumerate(matches):
        content_end = matches[i + 1][0] if i + 1 < len(matches) else len(text)
        content = text[end:content_end].strip()
        priority = SECTION_PRIORITY_MAP.get(name, SectionPriority.LOW)
        sections.append(DocumentSection(
            name=name,
            content=content,
            priority=priority,
            char_start=start,
            char_end=content_end,
        ))

    return ParsedDocument(
        doc_type=doc_type,
        sections=[s for s in sections if not s.is_empty],
        raw_text=text,
    )


# ── Chunker ────────────────────────────────────────────────────────────────────

def chunk_document(
    doc: ParsedDocument,
    chunk_size: int = 512,
    overlap_words: int = 50,
) -> list[dict]:
    """
    Convert a ParsedDocument into RAG-ready chunks.
    Each chunk is a dict with 'text' and 'metadata'.

    Strategy:
    - CRITICAL / HIGH sections: chunk at paragraph boundaries, keep chunks small
    - FULL TEXT: sliding window with overlap
    - Each chunk carries section name + priority in metadata for re-ranking
    """
    chunks = []

    for section in doc.sections:
        if section.is_empty:
            continue

        section_meta = {
            **doc.metadata,
            "section":      section.name,
            "section_priority": int(section.priority),
            "doc_type":     doc.doc_type,
        }

        if section.priority >= SectionPriority.HIGH:
            # Paragraph-aware chunking for important sections
            paragraphs = [p.strip() for p in section.content.split("\n\n") if p.strip()]
            current_chunk_words = []
            current_word_count = 0

            for para in paragraphs:
                para_words = para.split()
                if current_word_count + len(para_words) > chunk_size and current_chunk_words:
                    chunks.append({
                        "text":     " ".join(current_chunk_words),
                        "metadata": section_meta,
                    })
                    # Overlap: keep last overlap_words from previous chunk
                    current_chunk_words = current_chunk_words[-overlap_words:]
                    current_word_count  = len(current_chunk_words)

                current_chunk_words.extend(para_words)
                current_word_count += len(para_words)

            if current_chunk_words:
                chunks.append({
                    "text":     " ".join(current_chunk_words),
                    "metadata": section_meta,
                })

        else:
            # Sliding window for full text / lower priority sections
            words = section.content.split()
            for i in range(0, len(words), chunk_size - overlap_words):
                window = words[i: i + chunk_size]
                if len(window) < 30:   # skip tiny trailing chunks
                    continue
                chunks.append({
                    "text":     " ".join(window),
                    "metadata": section_meta,
                })

    return chunks
