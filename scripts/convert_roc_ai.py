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

# Force the user-provided API key following expiration
API_KEY = "REDACTED_API_KEY_HIDDEN"

client = genai.Client(api_key=API_KEY)

ROC_DIR = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\LexCode\Codals\md\ROC"
OUT_DIR = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\LexCode\Codals\md\clean\ROC"
os.makedirs(OUT_DIR, exist_ok=True)

PROMPT = """
Convert this legal PDF file into clean Markdown. 
Follow these STRICT rules:
1. **NO HEADERS/FOOTERS**: Do not include page numbers, top-of-page rule summaries (e.g., 'Rule 1', 'Rule 130'), or court system text at absolute page margins.
2. **CLEAN TEXT**: Remove garbage characters or mis-mappings (e.g., replace 'û' or 'ù' with standard hyphens '-', en-dashes '–', or em-dashes '—' based on reading flow content context).
3. **STRUCTURE**:
    - `RULE X` items should be `### RULE X` with its Title below it.
    - `Section Y. Title.` should be rendered exactly as found, with the description trailing.
    - Bullet points paragraphs should retain standard formatting.
4. **NO CHATTER**: Return ONLY the extracted Markdown contents.
"""

def convert_pdf_ai(filename):
    print(f"\n🚀 Processing PDF: {filename} via Gemini AI...")
    path = os.path.join(ROC_DIR, filename)
    out_path = os.path.join(OUT_DIR, filename.replace('.pdf', '.md'))

    try:
        print("  Uploading file to Gemini File API...")
        uploaded_file = client.files.upload(file=path)
        print(f"  Upload Complete: {uploaded_file.name}")

        print("  Generating Content...")
        response = client.models.generate_content(
            model='gemini-2.5-flash',
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
    print(f"\n📝 Processing DOCX: {filename} via Gemini AI...")
    path = os.path.join(ROC_DIR, filename)
    out_path = os.path.join(OUT_DIR, filename.replace('.docx', '.md'))
    
    try:
        doc = Document(path)
        full_text = '\n'.join([p.text for p in doc.paragraphs])
        
        print("  Generating Content for Docx...")
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[full_text, PROMPT]
        )
        
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"  ✅ Saved: {out_path}")
    except Exception as e:
        print(f"  ❌ Error processing {filename}: {e}")

def main():
    files = os.listdir(ROC_DIR)
    for f in files:
        if f.endswith('.pdf'):
            # Running PDF conversions
            convert_pdf_ai(f)
        elif f.endswith('.docx'):
            convert_docx(f)

if __name__ == "__main__":
    main()
