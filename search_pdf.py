import os
import fitz  # PyMuPDF

pdf_dir = r"C:\Users\rnlar\.gemini\antigravity\scratch\LexMatePH v3\pdf quamto"
search_term = "Silverio’s petition"

print(f"Searching for '{search_term}' in PDF files...")

found = False
for filename in os.listdir(pdf_dir):
    if filename.endswith(".pdf"):
        filepath = os.path.join(pdf_dir, filename)
        try:
            doc = fitz.open(filepath)
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text()
                if "Silverio" in text and "petition" in text:
                    print(f"\n--- Found in {filename} Page {page_num + 1} ---")
                    # Extract surrounding context
                    lines = text.split('\n')
                    for i, line in enumerate(lines):
                        if "Silverio" in line:
                            start = max(0, i - 10)
                            end = min(len(lines), i + 10)
                            print("\n".join(lines[start:end]))
                            found = True
                            break
            doc.close()
            if found:
                break
        except Exception as e:
            print(f"Error reading {filename}: {e}")

if not found:
    print("Not found in any PDF.")
