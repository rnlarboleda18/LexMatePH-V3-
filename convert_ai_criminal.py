import os
import fitz
from google import genai

# Setup Gemini API (New google-genai SDK)
API_KEY = "AIzaSyAJ1l_1D0rk0rupp-_NDASKpMDElIMY3Xw"
client = genai.Client(api_key=API_KEY)

SYSTEM_INSTRUCTION = """
You are a highly accurate legal document extraction AI. Your mission is to extract Bar Exam Questions, Sub-questions, and Answers VERBATIM from the provided text and format them in beautiful, structured Markdown.

FORMATTING RULES:
1. Every Question MUST start with a header exactly like this on its own line:
   Question ([Full Year(s)] BAR)
   
2. Follow this exact paragraph structure (Double Newlines between EVERY major element):

   Question (Year BAR)

   Q[Number][letter]:

   [Question Text]

   Suggested Answer

   A[Number][letter]:

   [Answer Text]

   ALTERNATIVE ANSWER:

   [Alternative Answer Text]

3. CRITICAL: 
   - Put a BLANK LINE after the Q#: marker and before the question text.
   - Put a BLANK LINE after the A#: marker and before the answer text.
   - Put a BLANK LINE before and after "Suggested Answer".
   - Start EVERY "ALTERNATIVE ANSWER:" on a NEW PARAGRAPH with a blank line before it.
   
4. VERBATIM: Do NOT paraphrase. Extract the law and text exactly as it appears.
5. CLEANUP: Exclude headers, footers, page numbers, and "Quamto" branding text.
6. SEQUENCE: Ensure questions are numbered sequentially starting from Q1.
7. OUTPUT ONLY THE MARKDOWN.
"""

def get_text_from_pdf(pdf_path, skip_pages=8):
    doc = fitz.open(pdf_path)
    full_text = ""
    for i in range(skip_pages, len(doc)):
        full_text += doc[i].get_text("text") + "\n\n"
    doc.close()
    return full_text

def run_test_criminal():
    pdf_path = r"C:\Users\rnlar\.gemini\antigravity\scratch\LexMatePH v3\pdf quamto\2_Criminal_Law_QUAMTO.pdf"
    out_md_path = r"C:\Users\rnlar\.gemini\antigravity\scratch\LexMatePH v3\pdf quamto\ai_md\2_Criminal_Law_QUAMTO_AI.md"
    
    print(f"Extracting text from {pdf_path}...")
    text = get_text_from_pdf(pdf_path)
    print(f"Extracted {len(text)} characters.")
    
    print("Calling Gemini 3-flash-preview (No Chunking)...")
    try:
        response = client.models.generate_content(
            model='gemini-3-flash-preview', 
            contents=text,
            config={
                'system_instruction': SYSTEM_INSTRUCTION
            }
        )
        
        markdown_output = response.text.strip()
        
        os.makedirs(os.path.dirname(out_md_path), exist_ok=True)
        with open(out_md_path, 'w', encoding='utf-8') as f:
            f.write(markdown_output)
        
        print(f"SUCCESS: Result saved to {out_md_path}")
        print(f"Result length: {len(markdown_output)} characters.")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    run_test_criminal()
