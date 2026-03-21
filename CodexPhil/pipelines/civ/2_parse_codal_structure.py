"""
Smart CIV HTML Parser - preserves structure with headers in correct positions
"""
from bs4 import BeautifulSoup
import re
import os

# Configuration
html_path = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\CodexPhil\Codals\doc\CIV_base.html"
output_path = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\CodexPhil\Codals\md\CIV_structured.md"

# Ensure directories exist
os.makedirs(os.path.dirname(output_path), exist_ok=True)

print(f"Reading HTML from: {html_path}")
with open(html_path, 'r', encoding='utf-8') as f:
    html_content = f.read()

print("Parsing CIV HTML with structure preservation...")

soup = BeautifulSoup(html_content, 'html.parser')

# Find all paragraphs - Lawphil's Civil Code structure is simpler (p align="center" vs justify)
paragraphs = soup.find_all('p')

print(f"Found {len(paragraphs)} paragraphs")

# Parse structure
markdown_parts = []
pending_headers = []  # Headers waiting to be attached to next article

for p in paragraphs:
    # Handle BR tags by replacing with newlines or spaces before getting text
    for br in p.find_all('br'):
        br.replace_with('\n')
        
    text = p.get_text().strip()
    if not text:
        continue
    
    # Get attributes
    align = p.get('align', '').lower()
    
    # Check if this is an article
    # "Article 1." or "Article 115."
    article_match = re.match(r'^Article\s+([0-9A-Za-z\-]+)\.\s*(.*)', text, re.IGNORECASE | re.DOTALL)
    
    if article_match:
        # This is an article!
        art_num = article_match.group(1)
        art_body = article_match.group(2).strip()
        
        # First, output any pending headers
        if pending_headers:
            for header in pending_headers:
                # Clean up header text (remove extra newlines)
                clean_header = header.replace('\n', ' ').strip()
                markdown_parts.append(f"## {clean_header}\n\n")
            pending_headers = []
        
        # Output article with ### header
        # We start with "### Article X.\n\nBody..."
        markdown_parts.append(f"### Article {art_num}.\n\n{art_body}\n\n")
    
    elif align == 'center':
        # Header (BOOK, TITLE, CHAPTER, or descriptive centered text)
        # Add to pending headers to be output before next article
        pending_headers.append(text)
    
    elif align == 'justify':
        # Regular body text?
        # Sometimes articles are split across paragraphs
        # If we have started writing articles, append to the last one
        
        # BUT: Check if it's really an article that missed regex (unlikely with this specific pages)
        # OR: It functions as a continuation of previous article
        
        if markdown_parts:
            # Append to last article
            # Remove last newlines, append text, add back
            markdown_parts[-1] = markdown_parts[-1].rstrip()
            markdown_parts[-1] += f"\n\n{text}\n\n"
        else:
            # Preamble text before any article?
            pending_headers.append(text)
            
    else:
        # No alignment specified - treat as generic text
        # If it looks like a header (uppercase, short), treat as header
        if text.isupper() and len(text) < 100:
             pending_headers.append(text)
        else:
            # Append to last part
            if markdown_parts:
                markdown_parts[-1] = markdown_parts[-1].rstrip()
                markdown_parts[-1] += f"\n\n{text}\n\n"

# Combine
final_markdown = ''.join(markdown_parts)

# Post-processing cleanups
# Fix run-in titles if any: "Article 1. - Title." -> "Article 1. Title."
final_markdown = re.sub(r'(### Article [0-9A-Za-z\-]+\.)[\s\-]*(.+)', r'\1 \2', final_markdown)

# Output stats
article_count = len(re.findall(r'^### Article', final_markdown, re.MULTILINE))
header_sections = len(re.findall(r'^## ', final_markdown, re.MULTILINE))

print(f"\n✅ Structured markdown created")
print(f"   Articles: {article_count}")
print(f"   Header sections: {header_sections}")
print(f"   Output: {output_path}")
print(f"   Size: {len(final_markdown)} characters")

with open(output_path, 'w', encoding='utf-8') as f:
    f.write(final_markdown)
