
import os
import sys
import re
import json
from google import genai
from google.genai import types

# --- Configuration ---
API_KEY = "REDACTED_API_KEY_HIDDEN"
try:
    with open('local.settings.json') as f:
        settings = json.load(f)
        if 'GOOGLE_API_KEY' in settings['Values']:
            API_KEY = settings['Values']['GOOGLE_API_KEY']
except:
    pass

client = genai.Client(api_key=API_KEY)

def clean_text(text):
    """
    Cleans up encoding artifacts and normalizes text.
    """
    text = text.replace("â€“", "-").replace("â€œ", '"').replace("â€", '"').replace("â€™", "'")
    return text

def parse_amendment_document(filepath):
    """
    Main entry point. Reads file, detects size, and chooses strategy.
    """
    print(f"Reading amendment file: {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Step 1: Clean Content
    content = clean_text(content)
    
    # Check size - if small (< 30k chars), use single shot
    if len(content) < 30000:
        return parse_full_document_ai(content)
    
    print(f"  [INFO] Large document detected ({len(content)} chars). Using batch processing...")
    return parse_chunked_document_ai(content)

def parse_metadata_ai(header_content):
    """
    Extracts purely metadata (ID, Date, Title) from the document header.
    """
    prompt = """Extract metadata from this legal document header.
    Return JSON: { "amendment_id": "string", "date": "YYYY-MM-DD", "title": "string" }
    
    Header content:
    """ + f"```\n{header_content}\n```"

    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt,
            config={"response_mime_type": "application/json", "temperature": 0.0}
        )
        return json.loads(response.text)
    except:
        return {}

def parse_full_document_ai(content):
    """
    Original single-shot logic for smaller files.
    """
    prompt = get_parser_prompt(content)
    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt,
            config={"response_mime_type": "application/json", "temperature": 0.0}
        )
        result = json.loads(response.text)
        return process_ai_result(result, content)
    except Exception as e:
        print(f"AI Parse Error: {e}")
        raise e

def parse_chunked_document_ai(content):
    """
    Splits large documents into chunks (by Section) and processes them iteratively.
    """
    # 1. Extract Metadata from the first 5000 chars
    metadata = parse_metadata_ai(content[:5000])
    
    # 2. Split by "**Section" or "Section"
    # We regex split but keep delimiters
    # Pattern: Look for "**Section" or just "Section" at start of line
    sections = re.split(r'(?=\n\s*(?:\*\*|)?Section\s+\d+)', content.strip())
    
    # Filter empty
    sections = [s for s in sections if s.strip()]
    
    # 3. Batch sections
    BATCH_SIZE = 15
    all_changes = []
    
    import math
    num_batches = math.ceil(len(sections) / BATCH_SIZE)
    
    print(f"  [INFO] Split into {len(sections)} sections. Processing in {num_batches} batches...")
    
    for i in range(0, len(sections), BATCH_SIZE):
        batch = sections[i:i+BATCH_SIZE]
        batch_text = "\n".join(batch)
        
        print(f"    Processing batch {i//BATCH_SIZE + 1}/{num_batches}...")
        
        prompt = get_parser_prompt(batch_text, extract_metadata=False)
        try:
            response = client.models.generate_content(
                model="gemini-3.0-flash",
                contents=prompt,
                config={"response_mime_type": "application/json", "temperature": 0.0}
            )
            result = json.loads(response.text)
            changes = result.get('changes', [])
            all_changes.extend(changes)
        except Exception as e:
            print(f"    [!] Error in batch {i//BATCH_SIZE + 1}: {e}")
            # Continue to next batch? Or fail? let's fail to be safe
            raise e
            
    # 4. Construct final object
    final_result = {
        "amendment_id": metadata.get('amendment_id'),
        "date": metadata.get('date'),
        "title": metadata.get('title'),
        "changes": all_changes
    }
    
    return process_ai_result(final_result, content)

def process_ai_result(result, raw_content):
    """
    Standardizes the AI JSON output.
    """
    cleaned_changes = []
    for change in result.get('changes', []):
        text = change.get('new_text', '').strip()
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1].strip()
            
        cleaned_changes.append({
            "article_number": str(change['article_number']), # Force string
            "new_text": text,
            "action": change.get("action", "amend").lower()
        })

    return {
        "amendment_id": result.get('amendment_id'),
        "date": result.get('date'),
        "title": result.get('title'),
        "changes": cleaned_changes,
        "raw_content": raw_content
    }

def get_parser_prompt(content, extract_metadata=True):
    meta_instruction = ""
    if extract_metadata:
        meta_instruction = """
    1. **amendment_id**: The identifier of the law.
    2. **date**: The date of approval (YYYY-MM-DD).
    3. **title**: The comprehensive title."""
    
    prompt = f"""You are a specialized Legal Text Parser.
    
    **CRITICAL INSTRUCTION - TEXTUAL FIDELITY:**
    When extracting "new_text", provide a **LITERAL, 100% EXACT COPY**.
    - NO PARAPHRASING.
    - PRESERVE PUNCTUATION.
    
    **Extraction Targets:**{meta_instruction}
    4. **changes**: List of amendments. For each:
       - **article_number**: String (e.g. "125", "172-A"). MUST capture suffix letters.
       - **new_text**: FULL body text (LITERAL COPY). If repealed, write "REPEALED".
       - **action**: "amend", "insert", or "repeal".

    **Input Document:**
    ```
    {content}
    ```

    **Output Format:**
    JSON: {{ "changes": [ {{ "article_number": "123", "new_text": "...", "action": "amend" }}, {{ "article_number": "172-A", "new_text": "...", "action": "insert" }} ] {', "amendment_id": "...", "date": "...", "title": "..."' if extract_metadata else ''} }}
    """
    return prompt

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", help="Path to amendment markdown file")
    args = parser.parse_args()
    
    if args.file:
        try:
            res = parse_amendment_document(args.file)
            print("Parsing successful!")
            print(json.dumps(res, indent=2))
        except Exception as e:
            print(f"Failed to parse: {e}")
            sys.exit(1)
