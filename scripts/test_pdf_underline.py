import fitz
import json

pdf_path = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\CodexPhil\Codals\md\ROC\ROC Evidence as amended 2019.pdf"

print(f"Opening: {pdf_path}")
doc = fitz.open(pdf_path)
page = doc[0]  # Check first page

# Test flags
TEXT_COLLECT_STYLES = 32768  # as from search result

try:
    # Try with dict and rawdict
    d1 = page.get_text("dict", flags=TEXT_COLLECT_STYLES)
    # Let's inspect first few spans
    found = False
    for block in d1["blocks"]:
        if "lines" in block:
            for line in block["lines"]:
                for span in line["spans"]:
                    # Print anything that might indicate decoration
                    if any(k in span for k in ["underline", "decoration", "style"]):
                        print(f"Span keys: {span.keys()}")
                        print(f"Span: {span}")
                        found = True
                    # Let's just print a span with multiple keys to see what's in there
                    if not found and len(span.get("text", "").strip()) > 3:
                         print(f"Sample Span keys: {span.keys()}")
                         print(f"Sample Span: {span}")
                         found = True
except Exception as e:
    print(f"Error: {e}")

doc.close()
