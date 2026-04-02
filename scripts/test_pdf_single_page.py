import os
import sys
import json

try:
    from google import genai
except ImportError:
    print("Installing google-genai...")
    os.system("pip install google-genai")
    from google import genai

API_KEY = "REDACTED_API_KEY_HIDDEN"
client = genai.Client(api_key=API_KEY)

PDF_PATH = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\LexCode\Codals\md\ROC\1. ROC Civil Procedure as amended 2019.pdf"

PROMPT = "Convert this legal PDF file into clean Markdown. Strict verbatim structure."

def test_single_page():
    # Split single page to be fast
    try:
         from pypdf import PdfWriter, PdfReader
    except ImportError:
         os.system("pip install pypdf")
         from pypdf import PdfWriter, PdfReader

    reader = PdfReader(PDF_PATH)
    writer = PdfWriter()
    writer.add_page(reader.pages[0]) # Page 1 only
    
    temp_pdf = "temp_debug_page1.pdf"
    with open(temp_pdf, 'wb') as f:
         writer.write(f)

    print("Uploading single page...")
    uploaded_file = client.files.upload(file=temp_pdf)
    print(f"Upload Complete: {uploaded_file.name}")

    print("Generating Content...")
    try:
        response = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=[uploaded_file, PROMPT]
        )
        print("\n--- Response Model Dump ---")
        print(str(response))
        print(f"\nResponse Text: {response.text!r}")
    except Exception as e:
        print(f"Error during generation: {e}")
    finally:
        client.files.delete(name=uploaded_file.name)
        if os.path.exists(temp_pdf):
             os.remove(temp_pdf)

if __name__ == "__main__":
    test_single_page()
