import os
import sys
import json

try:
    from pypdf import PdfWriter, PdfReader
except ImportError:
    print("Installing pypdf...")
    os.system("pip install pypdf")
    from pypdf import PdfWriter, PdfReader

try:
    from google import genai
except ImportError:
    print("Installing google-genai...")
    os.system("pip install google-genai")
    from google import genai

# Force API Key
API_KEY = "REDACTED_API_KEY_HIDDEN"
client = genai.Client(api_key=API_KEY)

ROC_DIR = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\CodexPhil\Codals\md\ROC"
OUT_DIR = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\CodexPhil\Codals\md\clean\ROC"

PROMPT = """
Convert this legal PDF file segment into clean Markdown. 
Follow these STRICT rules:
1. **STRICT VERBATIM**: Do NOT paraphrase, summarize, or restructure sentences. Adhere strictly to the words of the law.
2. **NO HEADERS/FOOTERS**: Do not include page numbers, top-of-page rule summaries (e.g., 'Rule 1', 'Rule 2'), or court system text at absolute page margins.
3. **STRUCTURE**:
    - `RULE X` items should be `### RULE X` with its Title below it.
    - `Section Y. Title.` should be rendered exactly as found, with description trailing.
4. **NO CHATTER**: Return ONLY the extracted Markdown contents.
"""

def split_and_convert():
    pdf_name = "1. ROC Civil Procedure as amended 2019.pdf"
    path = os.path.join(ROC_DIR, pdf_name)
    out_path = os.path.join(OUT_DIR, pdf_name.replace('.pdf', '.md'))
    
    # Clean output file first
    if os.path.exists(out_path):
         os.remove(out_path)

    print(f"\n🚀 Splitting heavy PDF 1: {pdf_name}...")
    reader = PdfReader(path)
    total_pages = len(reader.pages)
    print(f"  Total Pages: {total_pages}")

    # Process 1 page at a time for absolute stability
    chunk_size = 1
    all_chunks_text = []

    for i in range(0, total_pages, chunk_size):
        end_page = min(i + chunk_size, total_pages)
        print(f"\n  ➡ Processing Pages {i+1} to {end_page}...")
        
        writer = PdfWriter()
        for p_idx in range(i, end_page):
            writer.add_page(reader.pages[p_idx])
            
        temp_pdf = f"temp_chunk_{i+1}_{end_page}.pdf"
        with open(temp_pdf, 'wb') as f:
            writer.write(f)
            
        try:
             print("    Uploading chunk to Gemini File API...")
             uploaded_file = client.files.upload(file=temp_pdf)
             print(f"    Upload Complete: {uploaded_file.name}")

             print("    Generating Content for Chunk...")
             response = client.models.generate_content(
                 model='gemini-3-flash-preview',
                 contents=[uploaded_file, PROMPT]
             )
             
             if response.text:
                  all_chunks_text.append(response.text)
                  print(f"    ✅ Chunk {i+1}-{end_page} Transcribed ({len(response.text)} chars).")
             else:
                  print(f"    ❌ Warning: Chunk {i+1}-{end_page} yielded empty text candidates.")

             client.files.delete(name=uploaded_file.name)
        except Exception as e:
             print(f"    ❌ Error on Chunk {i+1}-{end_page}: {e}")
        finally:
             if os.path.exists(temp_pdf):
                  os.remove(temp_pdf)

    # Combine into 1
    if all_chunks_text:
         with open(out_path, 'w', encoding='utf-8') as f:
              f.write('\n\n'.join(all_chunks_text))
         print(f"\n🎉 Successfully saved combined split-transcriptions to: {out_path}")
    else:
         print("\n❌ Failed to transcribe any chunks absolute securely.")

if __name__ == "__main__":
    split_and_convert()
