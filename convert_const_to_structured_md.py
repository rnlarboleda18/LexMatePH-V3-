import re
from docx import Document
import os

def convert_docx_to_md(docx_path, md_path):
    if not os.path.exists(docx_path):
        print(f"Error: {docx_path} not found.")
        return

    doc = Document(docx_path)
    md_lines = []

    for para in doc.paragraphs:
        # Split paragraph into lines to handle internal hard line breaks
        para_lines = para.text.split('\n')
        
        # Alignment: CENTER is 1
        is_centered = para.alignment == 1 or (para.style and 'center' in para.style.name.lower())

        for line in para_lines:
            text = line.strip()
            if not text:
                continue

            # 1. Preamble
            if text.upper() == "PREAMBLE":
                md_lines.append(f"\n## PREAMBLE\n")
                continue

            # 2. Article Header (Centered, starts with ARTICLE)
            if is_centered and text.upper().startswith("ARTICLE"):
                md_lines.append(f"\n## {text}\n")
                continue

            # 3. Section Header (Starts with SECTION X.)
            # We use a regex to be flexible with "SECTION 1." or "Section 21."
            if re.match(r'^SECTION\s+\d+\.', text, re.IGNORECASE):
                md_lines.append(f"\n### {text}\n")
                continue

            # 4. Article Title or Sub-headers (Centered text)
            if is_centered:
                if md_lines and md_lines[-1].strip().startswith("## ARTICLE"):
                    # Only append if the line doesn't have a title yet
                    # "## ARTICLE II" has 3 tokens.
                    if len(md_lines[-1].strip().split()) <= 3:
                        md_lines[-1] = md_lines[-1].strip() + " " + text + "\n"
                        continue
                
                # Sub-header (e.g. "Education", "Language")
                md_lines.append(f"\n#### {text}\n")
                continue

            # 5. Standard Paragraph
            md_lines.append(text)

    # Save to MD
    os.makedirs(os.path.dirname(md_path), exist_ok=True)
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(md_lines))
    
    print(f"Conversion complete: {md_path}")

if __name__ == "__main__":
    SOURCE = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\CodexPhil\Codals\Word\1987 Philippine Constitution.docx"
    TARGET = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\CodexPhil\Codals\md\1987_Philippine_Constitution_Structured.md"
    convert_docx_to_md(SOURCE, TARGET)
