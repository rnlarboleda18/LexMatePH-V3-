from docx import Document
import os

DOCX_PATH = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\LexCode\Codals\Word\1987 Philippine Constitution.docx"

def check_art1():
    doc = Document(DOCX_PATH)
    found_preamble = False
    for i, para in enumerate(doc.paragraphs):
        text = para.text.strip()
        if "PREAMBLE" in text.upper():
            found_preamble = True
            print(f"[{i}] PREAMBLE FOUND: {repr(text)}")
        
        if found_preamble and i < 100: # Check the next 100 paragraphs
             if any(kw in text.upper() for kw in ["TERRITORY", "ARTICLE I"]):
                 alignment = para.alignment
                 style = para.style.name if para.style else "No style"
                 print(f"[{i}] {repr(text)} | Align: {alignment} | Style: {style}")

if __name__ == "__main__":
    check_art1()
