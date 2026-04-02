
import os
import sys
import json
import argparse
from datetime import datetime
from google import genai

# Import database and application logic from existing scripts
# We assume this script is in data/LexCode/scripts/
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from apply_amendment import apply_amendment_with_ai
from process_amendment import get_db_connection, fetch_current_article, apply_amendment_to_database

# Configuration
API_KEY = "REDACTED_API_KEY_HIDDEN"
# Initialize Client
client = genai.Client(api_key=API_KEY)

def parse_amendment_with_ai_model(content):
    """
    Uses Gemini to extract structured amendment data from raw text.
    Replaces the regex-based parse_amendment.py.
    """
    system_instruction = """You are a precise legal extraction engine. Your job is to extract amendments from Philippine legislative documents.
    
    Output a JSON object with this exact schema:
    {
        "amendment_id": "string (e.g., 'Republic Act No. 12' or 'Act No. 4117')",
        "date": "YYYY-MM-DD (string, date of approval)",
        "title": "string (the full title of the Act)",
        "changes": [
            {
                "article_number": "string (digits only, e.g. '80', '146')",
                "new_text": "string (the EXACT full text of the amended article. Do not include the 'Section X.' prefix. Do include the 'Art. 123' prefix if present in the text.)",
                "code_reference": "string (what code is being amended, e.g. 'Revised Penal Code')"
            }
        ]
    }
    
    CRITICAL RULES:
    1. Extract the "new_text" EXACTLY as it appears. Preserve punctuation, capitalization, and internal formatting.
    2. Do NOT summarize.
    3. If multiple articles are amended, list them all.
    4. If a section amends an article, capture the target article number.
    """

    response = client.models.generate_content(
        model="gemini-3-pro-preview",
        contents=f"Extract amendments from this document:\n\n{content}",
        config={
            "temperature": 0.0,
            "response_mime_type": "application/json",
            "system_instruction": system_instruction
        }
    )
    return json.loads(response.text)

def process_amendment_full_ai(file_path, code_short_name="RPC", dry_run=False):
    print(f"\n{'='*70}")
    print(f"FULL AI AMENDMENT PROCESSOR (Gemini 3 Pro Pipeline)")
    print(f"{'='*70}\n")
    
    # 1. Read File
    print(f"[1/4] Reading file: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 2. AI Extraction
    print(f"[2/4] AI Extraction Phase (Parsing)...")
    try:
        prompt = """You are a Legal Extraction Specialist. 
        Extract the following fields from the Philippine Law provided below:
        1. Amendment ID (e.g. "Republic Act No. 12")
        2. Date (YYYY-MM-DD)
        3. Title
        4. Changes: A list of every article amended, with its Article Number (digits) and the New Text (Verbatim).
        
        Return pure JSON.
        
        Document Content:
        """ + content
        
        response = client.models.generate_content(
            model="gemini-3-pro-preview",
            contents=prompt,
            config={"response_mime_type": "application/json"}
        )
        data = json.loads(response.text)
        
        # Handle list response (e.g. wrapped in [ ... ])
        if isinstance(data, list):
            if len(data) > 0:
                data = data[0]
            else:
                print(f"  ✗ AI returned empty list. Raw: {response.text}")
                return
        
        # Save to file for verification
        with open("ai_extraction_result.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        print(f"  ✓ Amendment ID: {data.get('amendment_id')}")
        print(f"  ✓ Date: {data.get('date')}")
        print(f"  ✓ Changes found: {len(data.get('changes', []))}")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"  ✗ AI Extraction Failed: {e}")
        try:
             print(f"  Raw Response: {response.text}")
        except: pass
        return

    # 3. Database Connection
    print(f"\n[3/4] Connecting to database...")
    conn = get_db_connection()
    if not conn:
        return

    try:
        cur = conn.cursor()
        cur.execute("SELECT code_id FROM legal_codes WHERE short_name = %s", (code_short_name,))
        row = cur.fetchone()
        if not row:
            print(f"  ✗ Code '{code_short_name}' not found")
            return
        code_id = row[0]
    except Exception as e:
        print(f"  ✗ DB Error: {e}")
        return

    # 4. Processing Loop (AI Application)
    print(f"\n[4/4] Processing Amendments (Application Phase)...")
    results = []
    
    for change in data.get('changes', []):
        art_num = change['article_number']
        new_text_raw = change['new_text'] # This is extracted by AI, but might include quotes etc.
        
        print(f"\n  Article {art_num}:")
        
        # Fetch current
        current = fetch_current_article(conn, code_id, art_num)
        if not current:
            print(f"    ✗ Article {art_num} not found in DB")
            continue
            
        print(f"    Current version found (valid from {current['valid_from']})")
        print(f"    Applying amendment with AI...")
        
        # We reuse the existing AI application logic which is robust
        # It takes (Old, New_Instruction) -> Merged
        # Here 'new_text_raw' IS the instruction essentially ("Read as follows: ...")
        
        ai_result = apply_amendment_with_ai(current['content'], new_text_raw)
        
        if ai_result['success']:
             print(f"    ✓ AI application successful (confidence: {ai_result['validation_result']['confidence_score']:.2f})")
             
             if not dry_run:
                 success = apply_amendment_to_database(
                     conn, code_id, art_num, 
                     ai_result['new_text'], 
                     data['amendment_id'], 
                     data['date'],
                     description=ai_result.get('description')
                 )
                 if success:
                     print("    ✓ Database Updated")
                 else:
                     print("    ✗ Database Update Failed")
             else:
                 print("    ⊘ Dry Run - No DB Update")
        else:
            # Check if it's a no-change scenario
            if ai_result.get('no_change'):
                print(f"    ⊘ Article not substantively modified by this amendment")
                results.append({"article": art_num, "success": True, "note": "No substantive change"})
                continue
            
            print(f"    ✗ AI Application Failed: {ai_result['error']}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Full AI Amendment Processor")
    parser.add_argument("file", help="Path to amendment file")
    parser.add_argument("--code", default="RPC", help="Short name of the legal code")
    parser.add_argument("--dry-run", action="store_true", help="Do not update the database")
    
    args = parser.parse_args()
    
    process_amendment_full_ai(args.file, args.code, args.dry_run)
