import fitz
import json

pdf_path = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\CodexPhil\Codals\md\ROC\ROC Evidence as amended 2019.pdf"
output_path = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\scripts\pdf_dict_dump.json"

print(f"Opening: {pdf_path}")
doc = fitz.open(pdf_path)
page = doc[0]  # First page

TEXT_COLLECT_STYLES = 32768

d1 = page.get_text("dict", flags=TEXT_COLLECT_STYLES)

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(d1, f, indent=4)

print(f"Saved: {output_path}")
doc.close()
