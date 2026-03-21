import fitz  # PyMuPDF
import os

def test_extract():
    pdf_path = r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\CodexPhil\Codals\md\ROC\ROC Evidence as amended 2019.pdf'
    
    if not os.path.exists(pdf_path):
        print("PDF Not Found!")
        return
        
    doc = fitz.open(pdf_path)
    print(f"Total Pages: {len(doc)}")
    
    # Extract Page 1
    page = doc[0]
    text = page.get_text()
    print("\n--- Page 1 Text ---")
    print(text[:2000]) # Print first 2000 chars
    
    doc.close()

if __name__ == "__main__":
    test_extract()
