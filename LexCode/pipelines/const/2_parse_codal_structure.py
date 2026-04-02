"""
Smart RPC HTML Parser - preserves structure with headers in correct positions
"""
from bs4 import BeautifulSoup
import re

# Read HTML
html_path = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\LexCode\Codals\doc\RPC_base.html"
with open(html_path, 'r', encoding='utf-8') as f:
    html_content = f.read()

print("Parsing RPC HTML with structure preservation...")

soup = BeautifulSoup(html_content, 'html.parser')

# Find blockquote (main content)
blockquote = soup.find('blockquote')
if not blockquote:
    blockquote = soup.body

# Extract all paragraphs in order
paragraphs = blockquote.find_all('p')

print(f"Found {len(paragraphs)} paragraphs")

# Parse structure
markdown_parts = []
pending_headers = []  # Headers waiting to be attached to next article

for p in paragraphs:
    text = p.get_text().strip()
    if not text:
        continue
    
    # Get class
    p_class = p.get('class', [])
    if isinstance(p_class, list):
        p_class = ' '.join(p_class)
    
    # Classify by class
    is_centered_bold = 'cb' in p_class  # BOOK ONE, ACT NO., etc.
    is_centered = 'c' in p_class  # Centered italic descriptions
    is_justified = 'jn' in p_class  # Normal body text
    
    # Check if this is an article
    article_match = re.match(r'Article\s+([0-9A-Za-z\-]+)\.', text, re.IGNORECASE)
    
    if article_match:
        # This is an article!
        art_num = article_match.group(1)
        
        # First, output any pending headers
        if pending_headers:
            for header in pending_headers:
                markdown_parts.append(f"{header}\n\n")
            pending_headers = []
        
        # Apply run-in title spacing fix
        fixed_text = re.sub(r'\.(\s*)-(\s*)', r'. - ', text)
        
        # Output article with ### header
        markdown_parts.append(f"### {fixed_text}\n\n")
    
    elif is_centered_bold or (text.isupper() and len(text) < 100 and re.match(r'^[A-Z\s]+$', text)):
        # This is a header (BOOK, TITLE, CHAPTER, etc.)
        # Add to pending headers to be output before next article
        pending_headers.append(text)
    
    elif is_centered:
        # Centered descriptive text (italicized)
        pending_headers.append(text)
    
    else:
        # Regular body text - should be part of previous article
        # Just append to last article
        if markdown_parts:
            # Remove last newlines, append text, add back
            markdown_parts[-1] = markdown_parts[-1].rstrip('\n')
            markdown_parts[-1] += f" {text}\n\n"

# Combine
final_markdown = ''.join(markdown_parts)

# Apply final spacing fix
final_markdown = re.sub(r'\.(\s*)-(\s*)', r'. - ', final_markdown)

# Save
output_path = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\LexCode\Codals\md\RPC_structured_v2.md"
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(final_markdown)

# Count articles and headers
article_count = len(re.findall(r'^### Article', final_markdown, re.MULTILINE))
header_sections = len(re.findall(r'^(BOOK|TITLE|CHAPTER|PRELIMINARY)', final_markdown, re.MULTILINE))

print(f"\n✅ Structured markdown created")
print(f"   Articles: {article_count}")
print(f"   Header sections: {header_sections}")
print(f"   Output: {output_path}")
print(f"   Size: {len(final_markdown)} characters")

# Show first 1000 chars
print(f"\nFirst 1000 characters:")
print(final_markdown[:1000])
