import os
import fitz
import time
import docx
import re
from google import genai

# Setup Gemini API (New google-genai SDK)
API_KEY = "AIzaSyAJ1l_1D0rk0rupp-_NDASKpMDElIMY3Xw"
client = genai.Client(api_key=API_KEY)

# Use High-Quality Gemini 3.0 Flash Preview
MODEL_ID = 'gemini-3-flash-preview'

SYSTEM_INSTRUCTION = """
You are a highly accurate legal document extraction AI. Your mission is to extract Bar Exam Questions, Sub-questions, and Answers VERBATIM from the provided text and format them in beautiful, structured Markdown.

FORMATTING RULES:
1. Every Question MUST start with a header exactly like this on its own line:
   Question ([Full Year(s)] BAR)
   
   (Example: Question (2018 BAR) or Question (2015, 2012, 1996 BAR))

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
6. OUTPUT ONLY THE MARKDOWN.
"""

def get_text_from_pdf(pdf_path, skip_pages=8):
    doc = fitz.open(pdf_path)
    full_text = ""
    for i in range(skip_pages, len(doc)):
        full_text += doc[i].get_text("text") + "\n\n"
    doc.close()
    return full_text

def get_text_from_docx(docx_path):
    doc = docx.Document(docx_path)
    full_text = ""
    for para in doc.paragraphs:
        full_text += para.text + "\n"
    return full_text

def chunk_text(text, max_chars=120000):
    # Split text by Q: or Question: to avoid splitting a question in the middle
    blocks = re.split(r'\n(?=Q\s*:|Q\.\s*:|Question\s*:)', text, flags=re.IGNORECASE)
    
    chunks = []
    current_chunk = ""
    for block in blocks:
        if len(current_chunk) + len(block) > max_chars:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = block
        else:
            current_chunk += "\n" + block
            
    if current_chunk:
        chunks.append(current_chunk.strip())
        
    return chunks

def extract_qa_ai(file_path, out_md_path):
    print(f"Starting AI Conversion for: {file_path}")
    
    if file_path.lower().endswith('.pdf'):
        text = get_text_from_pdf(file_path, skip_pages=8)
    elif file_path.lower().endswith('.docx'):
        text = get_text_from_docx(file_path)
    else:
        print("Unsupported file format.")
        return
    
    if not text.strip():
        print("Error: No text extracted from file.")
        return

    # Use Large Chunks (120k chars) for fewer calls but safe output limits
    chunks = chunk_text(text, max_chars=120000)
    print(f"Total Text Length: {len(text)} chars. Split into {len(chunks)} chunks.")

    os.makedirs(os.path.dirname(out_md_path), exist_ok=True)
    
    current_q_num = 1
    
    with open(out_md_path, 'w', encoding='utf-8') as f:
        f.write(f"# AI Extracted Q&A from {os.path.basename(file_path)}\n\n")
        f.flush()
        
        for idx, chunk in enumerate(chunks):
            print(f"  Processing chunk {idx + 1}/{len(chunks)} ({len(chunk)} characters)...")
            
            prompt = f"""
            Extract the Q&A pairs from the following text chunk. 
            Maintain the verbatim extraction and formatting as defined in the system instruction.
            Start numbering questions from Q{current_q_num} sequentially if possible, otherwise use the numbering from the text.

            TEXT CHUNK:
            {chunk}
            """
            
            # Retry loop for rate limits
            for attempt in range(5):
                try:
                    response = client.models.generate_content(
                        model=MODEL_ID,
                        contents=prompt,
                        config={'system_instruction': SYSTEM_INSTRUCTION}
                    )
                    
                    markdown_output = response.text.strip()
                    
                    if markdown_output:
                        f.write(markdown_output + "\n\n---\n\n")
                        f.flush()
                        
                        # Update current_q_num based on the last Q number found
                        q_nums = re.findall(r'^Q(\d+)[a-z]*:', markdown_output, re.MULTILINE)
                        if q_nums:
                            max_q_in_chunk = max([int(n) for n in q_nums])
                            current_q_num = max_q_in_chunk + 1
                            
                        print(f"    -> Success. Next Q number: {current_q_num}")
                        break # Successful processing
                    else:
                        print(f"    -> Empty response on attempt {attempt+1}")
                
                except Exception as e:
                    if "429" in str(e) or "quota" in str(e).lower():
                        print(f"    -> Rate limit hit. Waiting 60s (Attempt {attempt+1}/5)...")
                        time.sleep(60)
                    else:
                        print(f"    -> Error on attempt {attempt+1}: {e}")
                
                time.sleep(10) 
            
            # Brief pause between chunks to keep the API happy
            time.sleep(15) 
                
    print(f"Finished writing to {out_md_path}")

if __name__ == "__main__":
    quamto_dir = r"C:\Users\rnlar\.gemini\antigravity\scratch\LexMatePH v3\pdf quamto"
    out_dir = os.path.join(quamto_dir, "ai_md")
    
    # subjects defined by current known filenames
    files_to_process = []
    
    subjects = [
        "Quamto 2023 Civil Law.docx",
        "2_Criminal_Law_QUAMTO.pdf",
        "3_Labor_Law_QUAMTO.pdf",
        "4_Legal_Ethics_QUAMTO.pdf",
        "5_Political_Law_QUAMTO.pdf",
        "6_Commercial_Law_QQUAMTOL.pdf",
        "7_Remedial_Law_QUAMTOL.pdf",
        "8_Taxation_Law_QUAMTO.pdf"
    ]

    for f in subjects:
        file_path = os.path.join(quamto_dir, f)
        if not os.path.isfile(file_path): 
            print(f"Warning: Subject file not found: {file_path}")
            continue
        base_name = os.path.splitext(f)[0]
        out_md_path = os.path.join(out_dir, f"{base_name}_AI.md")
        files_to_process.append((file_path, out_md_path))

    for f_path, o_path in files_to_process:
        extract_qa_ai(f_path, o_path)
