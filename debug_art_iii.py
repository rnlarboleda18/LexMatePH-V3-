from docx import Document

def inspect_art_iii(docx_path):
    doc = Document(docx_path)
    found = False
    with open('art_iii_debug.txt', 'w', encoding='utf-8') as f:
        for i, p in enumerate(doc.paragraphs):
            text = p.text.strip()
            if 'ARTICLE III' in text.upper(): found = True
            if found:
                f.write(f"{i}: |{text}|\n")
                if 'ARTICLE IV' in text.upper(): break

if __name__ == "__main__":
    inspect_art_iii(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\CodexPhil\Codals\Word\1987 Philippine Constitution.docx")
