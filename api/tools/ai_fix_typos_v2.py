import fitz  # PyMuPDF
import os
import google.generativeai as genai

def extract_pdf_text(pdf_path):
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
         full_text += page.get_text() + "\n--- PAGE BREAK ---\n"
    doc.close()
    return full_text

def ai_correct_md(pdf_text, md_content, api_key):
    genai.configure(api_key=api_key)
    # Using gemini-3-flash-preview as requested
    model = genai.GenerativeModel('gemini-3-flash-preview') 
    
    prompt = f"""
You are an expert legal editor and formatting technician. 
Your task is to correct a Markdown (.md) file containing index items, by comparing it to the RAW TEXT extracted from the original PDF source to ensure exact matches in content.

The original PDF might have formatting artifacts, but the words are standard legal terms.
The Markdown file often has spaces inside words due to OCR ligature extraction issues (e.g., 'qualifi cations' instead of 'qualifications', 'confi ned' instead of 'confined').

Rules:
1. ONLY fix typos, structural spacing, or missing words where the PDF implies the actual complete English/legal word.
2. DO NOT change page dividers, sub-headers, or metadata if they are required for formatting.
3. PRESERVE all Markdown tags (e.g. `*`, `**`, `#`) and structures.
4. If a word simply has space splits like `fi ` -> `fi` or `fl ` -> `fl`, join it smoothly.
5. If you see spacing issues on section titles (e.g. 'Section 1. Evidence defi ned'), fix it to 'Section 1. Evidence defined'.
6. Return the **FULL UPDATED MARKDOWN CONTENT** without any surrounding preamble or explanation. Just the markdown.

--- RAW PDF TEXT START ---
{pdf_text}
--- RAW PDF TEXT END ---

--- MARKDOWN CONTENT TO FIX START ---
{md_content}
--- MARKDOWN CONTENT TO FIX END ---
    """
    
    try:
         print("Sending request to Gemini-3-flash-preview...")
         response = model.generate_content(prompt)
         return response.text, None
    except Exception as e:
         return md_content, str(e)

def main():
    api_key = r"REDACTED_API_KEY_HIDDEN"
    directory = r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\LexCode\Codals\md\ROC'
    
    files_to_process = [
        ('ROC Evidence as amended 2019.pdf', '4. ROC Evidence as amended 2019.md'),
        ('ROC Civil Procedure as amended 2019.pdf', '1. ROC Civil Procedure as amended 2019.md')
    ]
    
    for pdf_name, md_name in files_to_process:
        pdf_path = os.path.join(directory, pdf_name)
        md_path = os.path.join(directory, md_name)
        
        if not os.path.exists(pdf_path) or not os.path.exists(md_path):
             print(f"Skipping (Missing files): {pdf_name} / {md_name}")
             continue
             
        print(f"\nProcessing: {md_name}...")
        print("Extracting PDF text...")
        pdf_text = extract_pdf_text(pdf_path)
        
        with open(md_path, 'r', encoding='utf-8') as f:
             md_content = f.read()
             
        print(f"Comparing and fixing via AI...")
        fixed_md, error = ai_correct_md(pdf_text, md_content, api_key)
        
        if error:
             print(f"AI Error for {md_name}: {error}")
             continue
             
        if fixed_md and fixed_md != md_content:
             # Clean up any surrounding code block backticks Gemini often adds
             fixed_md = fixed_md.replace('```markdown\n', '').replace('```', '')
             if fixed_md.startswith('```'): fixed_md = fixed_md[3:] # fallback
             
             output_path = os.path.join(directory, md_name.replace('.md', '_fixed.md'))
             with open(output_path, 'w', encoding='utf-8') as f:
                  f.write(fixed_md)
             print(f"Saved fixed markdown to: {output_path}")
        else:
             print(f"No changes returned or suggested for {md_name}")

if __name__ == "__main__":
    main()
