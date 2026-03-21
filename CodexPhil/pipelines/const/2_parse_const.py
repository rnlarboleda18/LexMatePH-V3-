"""
Parse 1987 Constitution Structure (Article / Section)
"""
from bs4 import BeautifulSoup
import re
import os

# Configuration
BASE_DIR = r"c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2"
HTML_PATH = os.path.join(BASE_DIR, "CodexPhil", "Codals", "html", "CONST_base.html")
OUTPUT_PATH = os.path.join(BASE_DIR, "CodexPhil", "Codals", "md", "CONST_structured.md")

print(f"Reading from: {HTML_PATH}")

with open(HTML_PATH, 'r', encoding='utf-8') as f:
    html_content = f.read()

soup = BeautifulSoup(html_content, 'html.parser')

# Remove unwanted
for tag in soup(['script', 'style', 'meta', 'link', 'iframe']):
    tag.decompose()

# Extract content
# The structure helps us: Centered bold usually Article headers.
# Justified bold usually Section headers.

markdown_lines = []
is_started = False

# Get all paragraphs and headers?
# Lawphil structure uses <p> mostly.
elements = soup.find_all(['p', 'div', 'center', 'blockquote'])

print(f"Found {len(elements)} elements")

current_article = ""

for el in elements:
    text = el.get_text(separator=" ").strip()
    if not text:
        continue
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Check for Preamble
    if text.upper() == "PREAMBLE":
        is_started = True
        markdown_lines.append("\n## PREAMBLE\n")
        continue

    if not is_started:
        continue

    # Check for Article Header: "ARTICLE I NATIONAL TERRITORY"
    # Note: Lawphil often puts <br> between ARTICLE I and TITLE.
    # get_text(separator=" ") makes it "ARTICLE I NATIONAL TERRITORY"
    
    article_match = re.search(r'^(ARTICLE\s+[IVXLCDM]+)', text, re.IGNORECASE)
    if article_match and len(text) < 100: # Heuristic for header
        # Found Article Header
        markdown_lines.append(f"\n## {text}\n")
        current_article = text
        continue
        
    # Check for Section Header: "Section 1. ..."
    section_match = re.search(r'^Section\s+(\d+)\.', text)
    if section_match:
        # Found Section
        # We want "### Section 1. content..."
        # Or split?
        # Usually "Section 1. content" is in one paragraph.
        markdown_lines.append(f"\n### {text}\n")
        continue
        
    # Check for Subsection? "1. ..."
    # Check for definitions "A. ..." inside Article IX?
    
    # Just append text
    # If previous line was a header (## or ###), we don't need extra newline?
    # But text might be body of section.
    
    # If text is part of previous section...
    # Just append as paragraph
    markdown_lines.append(f"\n{text}\n")


final_md = "".join(markdown_lines)

# Post-processing cleanup
# Remove excess newlines
final_md = re.sub(r'\n{3,}', '\n\n', final_md)

with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    f.write(final_md)

print(f"Saved Structured Markdown to: {OUTPUT_PATH}")
print(f"Size: {len(final_md)} chars")

# Check parsing stats
articles = re.findall(r'^## ARTICLE', final_md, re.MULTILINE)
sections = re.findall(r'^### Section', final_md, re.MULTILINE)

print(f"Stats:")
print(f"  Articles: {len(articles)}")
print(f"  Sections: {len(sections)}")

print("\nFirst 1000 chars:")
print(final_md[:1000])
