"""
Debug 2: Parse 1987 Constitution from local file (No head decompose)
"""
import requests
from bs4 import BeautifulSoup
import re
import os

# Configuration
BASE_DIR = r"c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2"
HTML_PATH = os.path.join(BASE_DIR, "CodexPhil", "Codals", "html", "CONST_base.html")
MD_PATH = os.path.join(BASE_DIR, "CodexPhil", "Codals", "md", "CONST.md")

print(f"Reading from: {HTML_PATH}")

try:
    with open(HTML_PATH, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Parse HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    print("Soup created")

    # Remove unwanted elements - REMOVED 'head' from list
    # Because malformed HTML might put body inside head or vice versa
    for tag in soup(['script', 'style', 'meta', 'link', 'iframe']):
        tag.decompose()
    
    print("Cleaned tags (kept head)")

    # Extract text content
    content = soup.get_text()
    print(f"Extracted content length: {len(content)}")

    # Clean up
    lines = []
    for line in content.split('\n'):
        line = line.strip()
        if line:
            lines.append(line)

    full_text = '\n\n'.join(lines)
    print(f"Full text length: {len(full_text)}")

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
    os.makedirs(os.path.dirname(MD_PATH), exist_ok=True)
    with open(MD_PATH, 'w', encoding='utf-8') as f:
        f.write(full_text)

    print(f"Saved Markdown to: {MD_PATH}")
    print(f"Content length: {len(full_text)} characters")

    # Show first 500 chars
    print("\nFirst 500 characters:")
    print(full_text[:500])

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
