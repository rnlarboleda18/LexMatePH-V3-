from docx import Document
import re

def inspect_docx(docx_path):
    doc = Document(docx_path)
    
    with open('docx_structure_report.txt', 'w', encoding='utf-8') as f:
        found_art_iii = False
        found_art_xiv = False
        
        for i, p in enumerate(doc.paragraphs):
            text = p.text.strip()
            if not text: continue
            
            # Record alignment for all paragraphs matching ARTICLE XIV or ARTICLE III
            if "ARTICLE III" in text.upper(): found_art_iii = True
            if "ARTICLE XIV" in text.upper(): found_art_xiv = True
            if "ARTICLE XV" in text.upper(): found_art_xiv = False
            if "ARTICLE IV" in text.upper(): found_art_iii = False
            
            # Alignment: CENTER is 1
            align = p.alignment
            style_name = p.style.name if p.style else 'Unknown'
            
            # Check for bold in the first run
            is_bold = False
            if p.runs:
                is_bold = p.runs[0].bold
                
            if align == 1 or found_art_iii or found_art_xiv:
                f.write(f"Line {i}: [{align}] {style_name} (Bold:{is_bold}) | {text[:100]}\n")

if __name__ == "__main__":
    inspect_docx(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\LexCode\Codals\Word\1987 Philippine Constitution.docx")
