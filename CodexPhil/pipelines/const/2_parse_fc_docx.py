"""
Parse Family Code of the Philippines from DOCX to Structured Markdown
Structure: TITLE I (MARRIAGE) > Chapter 1 > Section X > Art. N.

Output format:
  ## TITLE I MARRIAGE
  ### Chapter 1. Requisites of Marriage
  #### Section 1. General Provisions
  ##### Art. 1. Content...
"""
import re
import os
from docx import Document

BASE_DIR = r"c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2"
DOCX_PATH = os.path.join(BASE_DIR, "CodexPhil", "Codals", "Word", "Family Code.docx")
OUTPUT_PATH = os.path.join(BASE_DIR, "CodexPhil", "Codals", "md", "FC_structured.md")

print(f"Reading from: {DOCX_PATH}")
doc = Document(DOCX_PATH)

markdown_lines = []
pending_title = None   # e.g. "TITLE I" - waiting for name on next Heading 5

# Pattern matchers
pat_title_only  = re.compile(r'^(TITLE\s+[IVXLCDM]+|\bTITLE\s+\d+)$', re.IGNORECASE)
pat_chapter     = re.compile(r'^(Chapter\s+\d+\..*)', re.IGNORECASE)
pat_section_hdr = re.compile(r'^(Section\s+\d+\..*)', re.IGNORECASE)
pat_art         = re.compile(r'^(Art\.|Article)\s+(\d+)\.(.*)', re.IGNORECASE)

for para in doc.paragraphs:
    text = para.text.strip()
    if not text:
        continue

    text = re.sub(r'\s+', ' ', text)
    style = para.style.name if para.style else ''

    # Main document heading (Heading 1)
    if style == 'Heading 1':
        markdown_lines.append(f"\n# {text}\n")
        continue

    # Check for TITLE-only line (e.g. "TITLE I") — next non-empty line is the title name
    if pat_title_only.match(text.upper().strip()):
        pending_title = text.upper().strip()
        continue

    # If we had a pending title, this line is the title name (usually Heading 5)
    if pending_title is not None:
        title_name = text.upper()
        markdown_lines.append(f"\n## {pending_title} {title_name}\n")
        pending_title = None
        continue

    # Heading 5/4/3/2 — used for Chapter or section titles
    if style in ('Heading 5', 'Heading 4', 'Heading 3', 'Heading 2'):
        if pat_chapter.match(text):
            markdown_lines.append(f"\n### {text}\n")
        elif pat_section_hdr.match(text):
            markdown_lines.append(f"\n#### {text}\n")
        else:
            markdown_lines.append(f"\n### {text}\n")
        continue

    # Chapter header (normal style that matches pattern)
    if pat_chapter.match(text):
        markdown_lines.append(f"\n### {text}\n")
        continue

    # Section sub-header (e.g. "Section 1. General Provisions")
    if pat_section_hdr.match(text):
        markdown_lines.append(f"\n#### {text}\n")
        continue

    # Article: "Art. 1. Content..." or "Article 1. Content..."
    m = pat_art.match(text)
    if m:
        # Reconstruct standard 'Art. X. Content' format
        art_prefix = f"Art. {m.group(2)}."
        rest_of_text = m.group(3)
        markdown_lines.append(f"\n##### {art_prefix}{rest_of_text}\n")
        continue

    # Plain body text
    markdown_lines.append(f"\n{text}\n")

final_md = "".join(markdown_lines)
final_md = re.sub(r'\n{3,}', '\n\n', final_md)

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    f.write(final_md)

print(f"Saved to: {OUTPUT_PATH}")

titles    = re.findall(r'^## TITLE', final_md, re.MULTILINE)
chapters  = re.findall(r'^### Chapter', final_md, re.MULTILINE)
sections  = re.findall(r'^#### Section', final_md, re.MULTILINE)
articles  = re.findall(r'^##### Art', final_md, re.MULTILINE)
print(f"Stats: {len(titles)} titles, {len(chapters)} chapters, {len(sections)} sections, {len(articles)} articles")
print("\nFirst 2000 chars:")
print(final_md[:2000])
