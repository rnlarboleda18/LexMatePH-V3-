import fitz, re, os
from pathlib import Path

# Setup
ROC_DIR = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\LexCode\Codals\md\ROC")
file_path = ROC_DIR / "1. ROC Civil Procedure as amended 2019.pdf"

# Imports and functions from convert_roc_files_to_md
import sys
sys.path.append(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2")
from scraper.convert_roc_files_to_md import convert_pdf_to_md

print(f"Converting isolated file: {file_path}")
md_content = convert_pdf_to_md(file_path)

output_name = "1. ROC Civil Procedure as amended 2019_TEST.md"
output_path = ROC_DIR / output_name

with open(output_path, "w", encoding="utf-8") as f:
    f.write(md_content)

print(f"Isolated Convert Saved to: {output_name}")
