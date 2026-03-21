import os
import json
import psycopg2
import google.generativeai as genai
import time
import logging
import re

# Configuration
API_KEY = "REDACTED_API_KEY_HIDDEN"
DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

genai.configure(api_key=API_KEY)
# Using Flash for speed as requested
MODEL_NAME = 'models/gemini-2.0-flash'
model = genai.GenerativeModel(MODEL_NAME)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_db_connection():
    return psycopg2.connect(DB_CONNECTION_STRING)

def fix_title_batch(limit=10):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Select cases DESC order. 
    # Use SKIP LOCKED to avoid stepping on Digesters toes.
    # Selecting ID and RAW_CONTENT.
    query = """
        SELECT id, raw_content 
        FROM supreme_decisions 
        WHERE raw_content IS NOT NULL 
          AND raw_content != ''
          AND title = UPPER(title) -- Only process ALL-CAPS titles (unfixed)
          AND title ~ '[A-Z]'      -- Ensure it has some letters
        ORDER BY date DESC 
        LIMIT %s 
        FOR UPDATE SKIP LOCKED
    """
    
    cur.execute(query, (limit,))
    cases = cur.fetchall()
    
    if not cases:
        logging.info("No cases available for locking.")
        conn.close()
        return 0
        
    logging.info(f"Processing {len(cases)} cases for Title Fixing...")
    
    for case in cases:
        case_id, content = case
        
        # 1. SPLIT CONTENT (Optimization: Don't read full text)
        # Find "DECISION" or "RESOLUTION" to split header
        # We look for it in the first 5000 chars to be safe.
        header_limit = 10000
        intro_chunk = content[:header_limit]
        
        # Regex to find the split point (case insensitive, standalone word on a line roughly)
        # We look for the STANDARD start of body like "D E C I S I O N" or "DECISION" or "RESOLUTION"
        match = re.search(r'(?:\n|^)\s*(?:D\s*E\s*C\s*I\s*S\s*I\s*O\s*N|R\s*E\s*S\s*O\s*L\s*U\s*T\s*I\s*O\s*N|DECISION|RESOLUTION)\s*(?:\n|$)', intro_chunk, re.IGNORECASE)
        
        split_idx = -1
        split_word = ""
        
        if match:
            split_idx = match.start()
            split_word = match.group(0)
            header_text = intro_chunk[:split_idx]
            # Verify we didn't miss too much
            remaining_body = content[split_idx:]
        else:
            # Fallback: Just take first 2000 chars if we can't find marker, 
            # OR ask AI to find the break? 
            # Optimization: If no decision marker, maybe it's short?
            # Let's take the first 30 lines?
            lines = content.split('\n')
            if len(lines) > 50:
                header_text = "\n".join(lines[:40])
                remaining_body = "\n".join(lines[40:])
            else:
                header_text = content
                remaining_body = ""

        # PROMPT
        prompt = f"""
        You are a Legal Editor.
        
        **TASK:**
        1. **Format Title:** Identify the Case Title in this text. Convert it from ALL-CAPS to **Title Case**.
           - Capitalize first letter of proper names/major words.
           - Lowercase conjunctions/prepositions (and, of, the, v.) unless first word.
           - **STRICTLY PRESERVE** abbreviations/acronyms in UPPERCASE (e.g., JR., SR., III, PH, USA, COMELEC, G.R., SC, PNP, NLRC).
           - Do NOT remove punctuation.
           
           Example Input: "MARCIAL O. DAGOT, JR. AND THE HEIRS OF EBUENGA, PETITIONERS"
           Example Output: "Marcial O. Dagot, Jr. and the Heirs of Ebuenga, Petitioners"
           
        2. **Center Headings:** Wrap the top-level headings (Republic of the Philippines, Supreme Court, Division, etc.) and the Title itself in HTML `<center>` tags (or verify they are visually centered).
           - Actually, just return the text formatted. If you need to adhere to "Format Case Title", just ensure the text is Cased correctly.
           - User Instruction: "Center all the heading up to word decision or resolution".
           - Please wrap the centered lines (Republic..., Court..., Title...) in `<center>LINE TEXT</center>`.
           
        **INPUT HEADER TEXT:**
        {header_text}
        
        **OUTPUT:**
        Return ONLY valid JSON:
        {
            "header_html": "The formatted header with <center> tags...",
            "clean_title": "The Title Case version of the case title (e.g. Person v. People)"
        }
        """
        
        try:
            response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
            try:
                data = json.loads(response.text)
            except:
                clean_text = response.text.replace('```json', '').replace('```', '').strip()
                data = json.loads(clean_text)
                
            fixed_header = data.get('header_html', '').strip()
            clean_title = data.get('clean_title', '').strip()
            
            # Remove any ``` code blocks if Gemini adds them
            fixed_header = fixed_header.replace('```html', '').replace('```', '').strip()
            
            # Reconstruct
            new_full_content = fixed_header + "\n" + remaining_body
            
            # Update DB - raw_content AND title
            cur.execute("""
                UPDATE supreme_decisions
                SET raw_content = %s,
                    title = COALESCE(%s, title)
                WHERE id = %s
            """, (new_full_content, clean_title, case_id))
            
            conn.commit()
            logging.info(f"Fixed Title Case ID {case_id} (Title: {clean_title[:30]}...)")
            time.sleep(1) # Go fast
            
        except Exception as e:
            logging.error(f"Error fixing Case ID {case_id}: {e}")
            conn.rollback()
            
    conn.close()
    return len(cases)

if __name__ == "__main__":
    while True:
        try:
            processed = fix_title_batch(limit=20)
            if processed == 0:
                logging.info("Gap in cases or lock contention. Sleeping...")
                time.sleep(5)
        except Exception as e:
            logging.error(f"Loop Crash: {e}")
            time.sleep(5)
