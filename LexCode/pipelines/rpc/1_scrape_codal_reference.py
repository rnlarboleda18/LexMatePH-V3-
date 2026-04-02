"""
Download base RPC from lawphil.net and convert to markdown
"""
import requests
from bs4 import BeautifulSoup
import re

# Download HTML
url = "https://lawphil.net/statutes/acts/act1930/act_3815_1930.html"
print(f"Downloading from: {url}")

response = requests.get(url)
response.raise_for_status()

# Save raw HTML
html_path = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\LexCode\Codals\doc\RPC_base.html"
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(response.text)

print(f"Saved HTML to: {html_path}")

# Parse HTML
soup = BeautifulSoup(response.content, 'html.parser')

# Remove unwanted elements
for tag in soup(['script', 'style', 'head', 'meta', 'link', 'iframe']):
    tag.decompose()

# Extract text content
# The RPC is usually in a blockquote or main content area
content = soup.get_text()

# Clean up
lines = []
for line in content.split('\n'):
    line = line.strip()
    if line:
        lines.append(line)

full_text = '\n\n'.join(lines)

# Remove lawphil watermarks
watermarks = [
    r"The Lawphil Project - Arellano Law Foundation",
    r"\(awÞhi\(", r"\(awÞhi", r"\(aw\w+",
    r"1a\w+phi1", r"1avvphi1", r"ℒαwρhi৷", r"ℒαwρhi",
    r"1awp\+\+i1", r"1wphi1", r"Lawphil",
    r"Arellano Law Foundation"
]
for pattern in watermarks:
    full_text = re.sub(pattern, "", full_text, flags=re.IGNORECASE)

# Fix merged run-in titles AUTOMATICALLY
# Pattern: "Title.-Body" should be "Title. - Body"
full_text = re.sub(r'\.(\s*)-(\s*)', r'. - ', full_text)

# Save markdown
md_path = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\LexCode\Codals\md\RPC.md"
with open(md_path, 'w', encoding='utf-8') as f:
    f.write(full_text)

print(f"Saved Markdown to: {md_path}")
print(f"Content length: {len(full_text)} characters")

# Show first 500 chars
print("\nFirst 500 characters:")
print(full_text[:500])
