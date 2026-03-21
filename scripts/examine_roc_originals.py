import os
import sys

# Attempt to import libraries, suggest pip if missing
try:
    import pdfplumber
except ImportError:
    print("Installing pdfplumber...")
    os.system("pip install pdfplumber")
    import pdfplumber

try:
    from docx import Document
except ImportError:
    print("Installing python-docx...")
    os.system("pip install python-docx")
    from docx import Document

ROC_DIR = r"C:\Users\rnlar\AppData\Local\Programs\Python\Python312\Lib\site-packages" 
# Better use relative or absolute path based on user's workspace
ROC_DIR = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\CodexPhil\Codals\md\ROC"

def examine_pdf(filename):
    path = os.path.join(ROC_DIR, filename)
    print(f"\n=== EXAMINING PDF: {filename} ===")
    try:
        with pdfplumber.open(path) as pdf:
             # Look at first 2 pages
             for i in range(min(2, len(pdf.pages))):
                 page = pdf.pages[i]
                 text = page.extract_text()
                 print(f"\n--- Page {i+1} Sample (First 600 chars) ---")
                 print(text[:600] if text else "No text extracted")
    except Exception as e:
         print(f"Error reading PDF: {e}")

def examine_docx(filename):
    path = os.path.join(ROC_DIR, filename)
    print(f"\n=== EXAMINING DOCX: {filename} ===")
    try:
        doc = Document(path)
        print("\n--- First 5 Paragraphs ---")
        for i, p in enumerate(doc.paragraphs[:5]):
             print(f"[{i}] {p.text}")
    except Exception as e:
         print(f"Error reading DOCX: {e}")

def main():
    files = os.listdir(ROC_DIR)
    for f in files:
        if f.endswith('.pdf'):
            examine_pdf(f)
        elif f.endswith('.docx'):
            examine_docx(f)

if __name__ == "__main__":
    main()
