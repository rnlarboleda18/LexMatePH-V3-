
from bs4 import BeautifulSoup
from markdownify import markdownify as md
import re
from pathlib import Path

html_path = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\lawphil_html\2025\gr_264724_2025.html")
html_content = html_path.read_text(encoding='cp1252', errors='replace')

def clean_soup_dom(soup):
    # Remove script/style tags
    for tag in soup(['script', 'style', 'header', 'footer', 'form', 'nav', 'iframe', 'button', 'input', 'select', 'textarea']):
        tag.decompose()
    
    # Remove link tags that are not stylesheets might be too aggressive?
    # Lawphil CSS is usually in <link>
    # Keeping it simple for now as per original code
    
    # Remove specific classes/ids
    for tag in soup.find_all(attrs={"class": ["header", "footer", "nav", "sidebar"]}):
        tag.decompose()
        
    for tag in soup.find_all(id=["header", "footer", "nav", "sidebar"]):
        tag.decompose()
        
    # Unwrap structural tags
    for tag in soup(['div', 'span', 'main', 'article', 'section', 'table', 'tbody', 'thead', 'tfoot', 'tr', 'td', 'th']):
        tag.unwrap()
        
    return soup

remaining_nt = []
extracted_footnotes = {}

# 1. Clean DOM
soup = BeautifulSoup(html_content, "html.parser")
soup = clean_soup_dom(soup)

# 2. Extract Footnotes (simulated)
# ... skipping full logic, just stripping them for test
# actually, let's keep it close to real logic
footnotes = soup.find_all(attrs={"class": ["fn", "footnote", "ref"]}) 
# Note: Lawphil usually uses <p class="jn"><nt>1</nt>... or similar at bottom
# The real code uses extract_and_destroy_footnotes

# 3. MD Convert
# Removed 'table' from strip, as we unwrapped it manually
text = md(str(soup), heading_style="ATX", strip=['a', 'img', 'blockquote', 'center', 'dir'])

# 4. Process Lines
lines = text.split('\n')
cleaned_lines = []
start_collecting = False

with open("debug_lines.txt", "w", encoding="utf-8") as f:
    for i, line in enumerate(lines):
        f.write(f"Line {i}: {repr(line)}\n")
        
        stripped = line.strip()
        if not stripped: continue
        
        # Simulate Top Trim
        if not start_collecting:
            header_text = stripped.upper().replace('*', '').strip()
            if "DIVISION" in header_text or "EN BANC" in header_text:
                print(f"MATCH FOUND at Line {i}: '{stripped}'")
                start_collecting = True
            else:
                continue

        # Simulate Bottom Trim
        if stripped.replace('*', '').strip().upper() == "FOOTNOTES":
            print(f"STOP MATCH at Line {i}: '{stripped}'")
            break

        cleaned_lines.append(stripped)

final_text = '\n\n'.join(cleaned_lines)
with open("debug_output.md", "w", encoding="utf-8") as f:
    f.write(final_text)


