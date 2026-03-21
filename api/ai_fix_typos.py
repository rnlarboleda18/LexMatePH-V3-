import fitz  # PyMuPDF
import os
import json
import google.generativeai as genai

def get_api_key():
    try:
        with open('api/local.settings.json') as f:
            settings = json.load(f)
            return settings['Values']['GOOGLE_API_KEY']
    except Exception as e:
         print(f"Error loading API key: {e}")
         return None

def extract_pdf_text(pdf_path):
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
         full_text += page.get_text() + "\n--- PAGE BREAK ---\n"
    doc.close()
    return full_text

def ai_correct_md(pdf_text, md_content):
    api_key = get_api_key()
    if not api_key:
         return md_content, "API Key missing."
         
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-pro')
    
    prompt = f"""
You are an expert legal editor and formatting technician. 
Your task is to correct a Markdown (.md) file containing index items, by comparing it to the RAW TEXT extracted from the original PDF source.

The original PDF often has spaces inside words due to ligature extraction issues (e.g., 'qualifi cations' instead of 'qualifications', 'confi ned' instead of 'confined').
The Markdown file might have these typos, or missing punctuation, or anomalous spacings.

Rules:
1. ONLY fix typos, structural spacing, or missing words where the PDF has them correct.
2. DO NOT change page dividers, sub-headers, or metadata if they are required for formatting.
3. PRESERVE all Markdown tags (e.g. `*`, `**`, `#`) and structures.
4. If a word simply has space splits like `fi ` -> `fi` or `fl ` -> `fl`, join it smoothly.
5. Return the **FULL UPDATED MARKDOWN CONTENT** without any surrounding preamble or explanation. Just the markdown.

--- RAW PDF TEXT START ---
{pdf_text}
--- RAW PDF TEXT END ---

--- MARKDOWN CONTENT TO FIX START ---
{md_content}
--- MARKDOWN CONTENT TO FIX END ---
    """
    
    try:
         print("Sending request to Gemini-1.5-pro...")
         response = model.generate_content(prompt)
         return response.text, None
    except Exception as e:
         return md_content, str(e)

def main():
    directory = r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\CodexPhil\Codals\md\ROC'
    pdf_path = os.path.join(directory, 'ROC Evidence as amended 2019.pdf')
    md_path = os.path.join(directory, '4. ROC Evidence as amended 2019.md')
    
    if not os.path.exists(pdf_path) or not os.path.exists(md_path):
         print("Files not found.")
         return
         
    print("Extracting PDF text...")
    pdf_text = extract_pdf_text(pdf_path)
    # Truncate to avoid absolute context saturation if too large, but 21 pages should be fine for Pro.
    # pdf_text = pdf_text[:100000] 
    
    with open(md_path, 'r', encoding='utf-8') as f:
         md_content = f.read()
         
    print(f"Comparing and fixing {os.path.basename(md_path)}...")
    fixed_md, error = ai_correct_md(pdf_text, md_content)
    
    if error:
         print(f"AI Error: {error}")
         return
         
    if fixed_md and fixed_md != md_content:
         # Clean up any surrounding code block backticks Gemini often adds
         fixed_md = fixed_md.replace('```markdown\n', '').replace('```', '')
         
         output_path = os.path.join(directory, '4. ROC Evidence as amended 2019_fixed.md')
         with open(output_path, 'w', encoding='utf-8') as f:
              f.write(fixed_md)
         print(f"Saved fixed markdown to: {output_path}")
    else:
         print("No changes returned or suggested.")

if __name__ == "__main__":
    main()
