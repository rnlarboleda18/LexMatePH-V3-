import fitz
import os

def print_all():
    pdf_path = r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\CodexPhil\Codals\md\ROC\ROC Evidence as amended 2019.pdf'
    if not os.path.exists(pdf_path): return
    
    doc = fitz.open(pdf_path)
    for i, page in enumerate(doc):
         print(f"\n--- PAGE {i+1} ---")
         print(page.get_text())
    doc.close()

if __name__ == "__main__":
    print_all()
