import fitz
import os

def dump_all():
    pdf_path = r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\LexCode\Codals\md\ROC\ROC Evidence as amended 2019.pdf'
    output_path = r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\api\evidence_pdf_text.txt'
    
    if not os.path.exists(pdf_path): return
    
    doc = fitz.open(pdf_path)
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, page in enumerate(doc):
             f.write(f"\n--- PAGE {i+1} ---\n")
             f.write(page.get_text())
    doc.close()
    print(f"Dumped text to {output_path}")

if __name__ == "__main__":
    dump_all()
