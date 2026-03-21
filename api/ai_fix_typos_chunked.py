import fitz  # PyMuPDF
import os
import re
import google.generativeai as genai

def extract_pdf_text(pdf_path):
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
         full_text += page.get_text() + "\n--- PAGE BREAK ---\n"
    doc.close()
    return full_text

def ai_correct_chunk(pdf_text_context, md_chunk, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-3-flash-preview') 
    
    prompt = f"""
You are an expert legal editor. 
Your task is to correct a CHUNK of a Markdown (.md) file containing Rules of Court index items by comparing it to the RAW PDF extracts.
We are processing the document in parts to respect tokens limitations.

Rules:
1. ONLY fix typos or OCR space splits (e.g. 'off ered' -> 'offered', 'fi xed' -> 'fixed').
2. DO NOT modify section titles or markdown weights unless they are spelled wrong.
3. PRESERVE all Markdown tags exactly.
4. Return ONLY the **FULL UPDATED CHUNK MARKDOWN** without any explanation or ``` delimiters.

--- RAW PDF TEXT CONTEXT START ---
{pdf_text_context}
--- RAW PDF TEXT CONTEXT END ---

--- MARKDOWN CHUNK TO FIX START ---
{md_chunk}
--- MARKDOWN CHUNK TO FIX END ---
    """
    try:
         response = model.generate_content(prompt)
         return response.text, None
    except Exception as e:
         return md_chunk, str(e)

def split_md(md_content):
    # Split by headers that mark large breaks (e.g. '### RULE')
    # Use regex to find starts of '### RULE X' or similar
    pattern = r'(?=\n### RULE )'
    chunks = re.split(pattern, md_content)
    return chunks

def main():
    api_key = r"REDACTED_API_KEY_HIDDEN"
    directory = r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\CodexPhil\Codals\md\ROC'
    
    # We will process Civil Procedure (Large file)
    pdf_name = 'ROC Civil Procedure as amended 2019.pdf'
    md_name = '1. ROC Civil Procedure as amended 2019.md'
    
    pdf_path = os.path.join(directory, pdf_name)
    md_path = os.path.join(directory, md_name)
    
    if not os.path.exists(pdf_path) or not os.path.exists(md_path):
         print(f"File not found: {pdf_name} or {md_name}")
         return
         
    print(f"\nProcessing Chunked: {md_name}...")
    print("Extracting PDF text...")
    pdf_text = extract_pdf_text(pdf_path)
    
    # We pass the full PDF text or a sliced window context to chunk parser to align things properly,
    # but 100k pdf tokens input context IS supported, it's just the OUTPUT back to us that is capped!
    # So we can pass FULL PDF text input context to ALL chunks so the AI has complete structural lookup!
    
    with open(md_path, 'r', encoding='utf-8') as f:
         md_content = f.read()
         
    import concurrent.futures

    chunks = split_md(md_content)
    print(f"Split document into {len(chunks)} chunks.")
    
    fixed_chunks = [None] * len(chunks)
    
    def process_chunk_indexed(index, chunk):
         if not chunk.strip(): return index, ""
         print(f"Processing chunk {index+1}/{len(chunks)}...")
         # Pass pdf_text context fully 
         fixed_chunk, error = ai_correct_chunk(pdf_text, chunk, api_key)
         if error:
              print(f"Chunk {index+1} Error: {error}")
              return index, chunk
         fixed_chunk = fixed_chunk.replace('```markdown\n', '').replace('```', '')
         return index, fixed_chunk

    print("Sending requests in parallel (10 workers)...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
         future_to_index = {executor.submit(process_chunk_indexed, i, chunk): i for i, chunk in enumerate(chunks)}
         for future in concurrent.futures.as_completed(future_to_index):
              index, result = future.result()
              fixed_chunks[index] = result
              
    final_md = "".join(fixed_chunks)
    output_path = os.path.join(directory, md_name.replace('.md', '_fixed_chunked.md'))
    with open(output_path, 'w', encoding='utf-8') as f:
         f.write(final_md)
         
    print(f"Saved fixed chunked markdown to: {output_path}")

if __name__ == "__main__":
    main()
