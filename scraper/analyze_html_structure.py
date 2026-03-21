
import re
from pathlib import Path

path = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\lawphil_html\2018\gr_237428_2018.html")
if not path.exists():
    print(f"File not found: {path}")
    exit(1)

with open(path, 'r', encoding='cp1252', errors='replace') as f:
    text = f.read()

# 1. Search for citation context
target = "Integrity connotes"
idx = text.find(target)
if idx != -1:
    start = max(0, idx - 100)
    end = min(len(text), idx + 100)
    print("--- CITATION CONTEXT ---")
    print(text[start:end])
    print("------------------------\n")
else:
    print(f"'{target}' not found.")

# 2. Search for Footnotes section
footnotes_idx = text.find("FOOTNOTES")
if footnotes_idx == -1:
    footnotes_idx = text.find("Footnotes")

if footnotes_idx != -1:
    print("--- FOOTNOTES SECTION START ---")
    print(text[footnotes_idx:footnotes_idx+1000])
    print("-------------------------------")
else:
    print("Footnotes header not found.")
