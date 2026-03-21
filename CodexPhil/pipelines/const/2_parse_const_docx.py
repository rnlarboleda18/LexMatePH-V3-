import re
import os
from docx import Document

# Configuration
BASE_DIR = r"c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2"
DOCX_PATH = os.path.join(BASE_DIR, "CodexPhil", "Codals", "Word", "1987 Philippine Constitution.docx")
OUTPUT_PATH = os.path.join(BASE_DIR, "CodexPhil", "Codals", "md", "CONST_structured.md")

print(f"Reading from: {DOCX_PATH}")

doc = Document(DOCX_PATH)
markdown_lines = []

pending_article = None

for para in doc.paragraphs:
    text = para.text.strip()
    if not text:
        continue
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Check for Preamble
    if text.upper() == "PREAMBLE":
        markdown_lines.append("\n## PREAMBLE\n")
        continue

    # If we have a pending article, this line is the title
    if pending_article:
        markdown_lines.append(f"\n## {pending_article} {text.upper()}\n")
        pending_article = None
        continue

    # Check for Article Header: "ARTICLE I"
    article_match = re.search(r'^(ARTICLE\s+[IVXLCDM]+)', text, re.IGNORECASE)
    if article_match and len(text) < 150: # Heuristic for header
        if text.strip().upper() == article_match.group(1).upper():
            # Only the article number, title is on the next line
            pending_article = text.upper()
        else:
            # Title is on the same line
            markdown_lines.append(f"\n## {text.upper()}\n")
        continue
        
    # Check for Section Header: "Section 1. ..."
    section_match = re.search(r'^(Section|SECTION)\s+(\d+)\.', text)
    if section_match:
        markdown_lines.append(f"\n### {text}\n")
        continue
        
    # Just append text
    markdown_lines.append(f"\n{text}\n")

final_md = "".join(markdown_lines)

# Post-processing cleanup
final_md = re.sub(r'\n{3,}', '\n\n', final_md)

with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    f.write(final_md)

print(f"Saved Structured Markdown to: {OUTPUT_PATH}")
print(f"Size: {len(final_md)} chars")

# Check parsing stats
articles = re.findall(r'^## ARTICLE', final_md, re.MULTILINE)
sections = re.findall(r'^### Section|^### SECTION', final_md, re.MULTILINE)

print(f"Stats:")
print(f"  Articles: {len(articles)}")
print(f"  Sections: {len(sections)}")

print("\nFirst 1000 chars:")
print(final_md[:1000])
