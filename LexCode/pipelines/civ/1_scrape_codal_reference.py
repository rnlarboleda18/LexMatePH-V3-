import requests
from bs4 import BeautifulSoup
import re
import os

# Configuration for Civil Code
url = "https://lawphil.net/statutes/repacts/ra1949/ra_386_1949.html"
html_path = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\LexCode\Codals\doc\CIV_base.html"
md_path = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\LexCode\Codals\md\CIV.md"

# Ensure directories exist
os.makedirs(os.path.dirname(html_path), exist_ok=True)
os.makedirs(os.path.dirname(md_path), exist_ok=True)

print(f"Downloading from: {url}")
try:
    response = requests.get(url)
    response.raise_for_status()
except Exception as e:
    print(f"Error downloading: {e}")
    exit(1)

# Save raw HTML
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(response.text)
print(f"Saved raw HTML to: {html_path}")

# Parse HTML
soup = BeautifulSoup(response.content, 'html.parser')

# Remove unwanted elements
for tag in soup(['script', 'style', 'head', 'meta', 'link', 'iframe']):
    tag.decompose()

# Extract text content
content = soup.get_text()

# Clean up whitespace
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

# Fix merged run-in titles (e.g. "Title.-Body" -> "Title. - Body")
full_text = re.sub(r'\.(\s*)-(\s*)', r'. - ', full_text)

# Save markdown
with open(md_path, 'w', encoding='utf-8') as f:
    f.write(full_text)

print(f"Saved Cleaned Markdown (Flat) to: {md_path}")
print(f"Content length: {len(full_text)} characters")
print("Step 0 (Scraping) Complete.")
