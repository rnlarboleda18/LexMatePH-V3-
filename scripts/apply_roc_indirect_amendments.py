import os
import json
import re
import psycopg2
import google.generativeai as genai

# Configure Gemini
API_KEY = "REDACTED_API_KEY_HIDDEN"
genai.configure(api_key=API_KEY)

def get_db_connection():
    try:
        with open('api/local.settings.json') as f:
            settings = json.load(f)
            conn_str = settings['Values']['DB_CONNECTION_STRING']
    except Exception:
        conn_str = "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"
    return psycopg2.connect(conn_str)

def parse_docx_text_with_ai(txt_content):
    prompt = """
    You are a Legal Text Analyzer. Extract a list of implied amendments from this text document.
    
    For each amendment, identify:
    1. **Rule Numbers**: A list of rule numbers (e.g. ["110"], ["73", "74"]). Split multiple Rules if joined by '&' or 'and'.
    2. **Impact Instrument**: The Supreme Court Circular, DOJ Memo, or RA Statute being cited.
    3. **Date**: High certainty Date when the law was published (e.g., "2024-01-01") if known, or estimate based on year mentioned.
    4. **Description**: The background description from the text.
    5. **Effect**: The practical effect clauses on the Procedure.
    
    Return JSON format:
    {
       "amendments": [
          {
             "rule_nums": ["110"],
             "instrument": "DOJ Dept Circular 015",
             "date": "2024-01-15",
             "description": "...",
             "effect": "..."
          }
       ]
    }
    
    Text Content:
    """ + f"```\n{txt_content}\n```"

    model = genai.GenerativeModel("gemini-3-flash-preview")
    response = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json"}
    )
    return json.loads(response.text)

def main():
    txt_path = "scripts/docx_out.txt"
    if not os.path.exists(txt_path):
         print(f"File not found: {txt_path}")
         return

    with open(txt_path, 'r', encoding='utf-8') as f:
         content = f.read()

    print("Parsing text with Gemini AI...")
    parsed = parse_docx_text_with_ai(content)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
         # Get Code ID for ROC
         cur.execute("SELECT code_id FROM legal_codes WHERE short_name = 'ROC'")
         row = cur.fetchone()
         if not row:
              print("ROC code not found in legal_codes.")
              return
         code_id = row[0]
         
         for item in parsed.get('amendments', []):
              desc = f"{item['description']}\n\nEffect: {item['effect']}"
              instrument = item['instrument']
              date = item.get('date', '2024-01-01') # Default fallback
              rules = item['rule_nums']
              
              print(f"\nProcessing Instrument: {instrument} for Rules: {rules}")
              
              for r_num in rules:
                   print(f"  > Rule {r_num}...")
                   
                   # 1. Fetch ALL current active sections belonging to this Rule in roc_codal
                   # Continuous format: "Rule X, Section Y"
                   cur.execute("SELECT id, rule_section_label, amendments FROM roc_codal WHERE rule_section_label LIKE %s", (f"Rule {r_num},%",))
                   sections = cur.fetchall()
                   
                   if not sections:
                        print(f"    [-] No sections found for Rule {r_num} in roc_codal.")
                        continue
                        
                   for s in sections:
                        id_roc, article_num, existing_amendments = s
                        print(f"    Updating {article_num}...")
                        
                        # 2. Fetch current active version in `article_versions` to carry over content text
                        cur.execute("""
                            SELECT content 
                            FROM article_versions 
                            WHERE code_id = %s AND article_number = %s AND valid_to IS NULL
                            LIMIT 1
                        """, (code_id, article_num))
                        v_row = cur.fetchone()
                        
                        if not v_row:
                             print(f"    [!] No active version in article_versions for {article_num}")
                             continue
                        content_md = v_row[0]
                        
                        # 3. Close current version in article_versions
                        cur.execute("""
                            UPDATE article_versions 
                            SET valid_to = %s 
                            WHERE code_id = %s AND article_number = %s AND valid_to IS NULL
                        """, (date, code_id, article_num))
                        
                        # 4. Insert New Version with amendment payload
                        cur.execute("""
                            INSERT INTO article_versions 
                            (code_id, article_number, content, valid_from, valid_to, amendment_id, amendment_description)
                            VALUES (%s, %s, %s, %s, NULL, %s, %s)
                        """, (code_id, article_num, content_md, date, instrument, desc))
                        
                        # 5. Sync to `roc_codal` amendments array
                        am_list = []
                        if existing_amendments:
                             if isinstance(existing_amendments, str):
                                  am_list = json.loads(existing_amendments)
                             elif isinstance(existing_amendments, list):
                                  am_list = existing_amendments
                                  
                        if not any(a.get('id') == instrument for a in am_list):
                             am_list.append({
                                 "id": instrument,
                                 "date": date,
                                 "description": desc
                             })
                             
                        cur.execute("""
                            UPDATE roc_codal 
                            SET amendments = %s, updated_at = NOW() 
                            WHERE id = %s
                        """, (json.dumps(am_list), id_roc))
                        
                   print(f"    [OK] Finished Rule {r_num}")
                   
         conn.commit()
         print("\nAll indirect amendments synced into article_versions and roc_codal.")
         
    except Exception as e:
         conn.rollback()
         print(f"Error during ingestion: {e}")
    finally:
         cur.close()
         conn.close()

if __name__ == "__main__":
    main()
