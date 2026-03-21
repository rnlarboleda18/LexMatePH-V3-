import os
import sys
import json
import re

# Install SDK if missing
try:
    from google import genai
except ImportError:
    print("Installing google-genai...")
    os.system("pip install google-genai")
    from google import genai

try:
    from docx import Document
except ImportError:
    print("Installing python-docx...")
    os.system("pip install python-docx")
    from docx import Document

# Force user provided API key
API_KEY = "REDACTED_API_KEY_HIDDEN"
client = genai.Client(api_key=API_KEY)

ROC_DIR = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\CodexPhil\Codals\md\ROC"
OUT_DIR = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\CodexPhil\Codals\md\clean\ROC"
os.makedirs(OUT_DIR, exist_ok=True)

# Strict Prompt Guidelines
PROMPT = """
Convert this legal file into clean Markdown. 
Follow these STRICT rules:
1. **STRICT VERBATIM**: Do NOT paraphrase, summarize, or restructure sentences. Adhere strictly to the words of the law. Do NOT correct grammar or spelling unless it is an extremely obvious, broken typographical error that occurred from transcription layout.
2. **NO HEADERS/FOOTERS**: Do not include page numbers, top-of-page rule summaries (e.g., 'Rule 1', 'Rules 1-2'), or court system text from absolute page margins.
3. **CLEAN TEXT**: Remove garbage characters (e.g., replace 'û' or 'ù' with standard hyphens '-', en-dashes '–', or em-dashes '—' based on reading flow context).
4. **STRUCTURE**:
    - `RULE X` items should be `### RULE X` with its Title below it.
    - `Section Y. Title.` should be rendered exactly as found, with description trailing.
5. **NO CHATTER**: Return ONLY the extracted Markdown contents.
"""

# Ordered list of files to combine in sequence
FILE_SEQUENCE = [
    "1. ROC Civil Procedure as amended 2019.pdf",
    "2. ROC Special Proceeding.docx",
    "3. ROC Criminal Procedure.docx",
    "4. ROC Evidence as amended 2019.pdf"
]

def convert_pdf_ai(filename):
    print(f"\n🚀 Processing PDF: {filename} via gemini-3-flash-preview...")
    path = os.path.join(ROC_DIR, filename)
    out_path = os.path.join(OUT_DIR, filename.replace('.pdf', '.md'))

    try:
        print("  Uploading file to Gemini File API...")
        uploaded_file = client.files.upload(file=path)
        print(f"  Upload Complete: {uploaded_file.name}")

        print("  Generating Content...")
        response = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=[uploaded_file, PROMPT]
        )
        
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"  ✅ Saved: {out_path}")

        # Clean up file from cloud
        client.files.delete(name=uploaded_file.name)
    except Exception as e:
        print(f"  ❌ Error processing {filename}: {e}")

def convert_docx(filename):
    print(f"\n📝 Processing DOCX: {filename} via gemini-3-flash-preview...")
    path = os.path.join(ROC_DIR, filename)
    out_path = os.path.join(OUT_DIR, filename.replace('.docx', '.md'))
    
    try:
        doc = Document(path)
        full_text = '\n'.join([p.text for p in doc.paragraphs])
        
        print("  Generating Content for Docx...")
        response = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=[full_text, PROMPT]
        )
        
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"  ✅ Saved: {out_path}")
    except Exception as e:
        print(f"  ❌ Error processing {filename}: {e}")

def combine_files():
    combined_path = os.path.join(OUT_DIR, "Combined_Rules_of_Court.md")
    print(f"\n🔗 Combining all clean rules into: {combined_path}")
    
    with open(combined_path, 'w', encoding='utf-8') as outfile:
        for f_name in FILE_SEQUENCE:
            md_name = f_name.replace('.pdf', '.md').replace('.docx', '.md')
            md_path = os.path.join(OUT_DIR, md_name)
            if os.path.exists(md_path):
                print(f"  Appending {md_name}...")
                with open(md_path, 'r', encoding='utf-8') as infile:
                    content = infile.read()
                    outfile.write(f"\n\n# {f_name.split('. ', 1)[1].rsplit('.', 1)[0]}\n\n")
                    outfile.write(content)
                    outfile.write("\n\n---\n")
            else:
                 print(f"  ⚠️ Warning: {md_name} missing, skipping.")
    print("🎉 Combined file successfully created!")

def main():
    # Execute conversions based on ordered sequence
    for f in FILE_SEQUENCE:
        if f.endswith('.pdf'):
            convert_pdf_ai(f)
        elif f.endswith('.docx'):
            convert_docx(f)
    
    # After all files convert, combine them
    combine_files()

if __name__ == "__main__":
    main()
