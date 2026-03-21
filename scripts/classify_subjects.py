import os
import json
import psycopg2
import google.generativeai as genai
import time
import logging
import argparse

# Reuse config
API_KEY = "REDACTED_API_KEY_HIDDEN" 
DB_CONNECTION_STRING = "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

genai.configure(api_key=API_KEY)
# Using Flash for speed/cost, even for this lighter task
model = genai.GenerativeModel('models/gemini-2.0-flash')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - CLASSIFIER - %(message)s')

def get_db_connection():
    return psycopg2.connect(DB_CONNECTION_STRING)

def classify_batch(limit=20):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Select cases that HAVE a digest but NO subject
    query = """
        SELECT id, title, digest_facts, digest_issues, digest_ruling
        FROM supreme_decisions
        WHERE digest_facts IS NOT NULL 
          AND subject IS NULL
        LIMIT %s FOR UPDATE SKIP LOCKED
    """
    
    cur.execute(query, (limit,))
    cases = cur.fetchall()
    
    if not cases:
        conn.close()
        return 0
        
    logging.info(f"Processing batch of {len(cases)} cases for classification...")
    
    for case in cases:
        cid, title, facts, issues, ruling = case
        
        # Construct a lean prompt
        prompt = f"""
        You are a legal expert. 
        Classify the following Philippine Supreme Court case into ONE of the 8 Bar Subjects based on its Digest.
        
        **Subjects:**
        [
            "Political Law",
            "Civil Law", 
            "Commercial Law",
            "Labor Law and Social Legislation",
            "Criminal Law",
            "Taxation Law",
            "Legal Ethics",
            "Remedial Law"
        ]
        
        **Context:**
        Title: {title}
        Facts: {facts[:1000]}...
        Issues: {issues}
        Ruling: {ruling[:1000]}...
        
        **Instructions:**
        - Choose the MAIN subject.
        - Return ONLY a raw JSON string: {{"subject": "Chosen Subject"}}
        """
        
        try:
            response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
            text = response.text.strip()
            
            # Cleanup markdown if present
            if text.startswith("```json"):
                text = text[7:-3].strip()
            elif text.startswith("```"):
                text = text[3:-3].strip()
                
            data = json.loads(text)
            subject = data.get("subject")
            
            if subject:
                cur.execute("UPDATE supreme_decisions SET subject = %s WHERE id = %s", (subject, cid))
                conn.commit()
                # logging.info(f"Classified ID {cid}: {subject}")
            else:
                logging.warning(f"No subject returned for ID {cid}")
                
            time.sleep(0.5) # Fast throttle
            
        except Exception as e:
            logging.error(f"Error classifying ID {cid}: {e}")
            conn.rollback()
            
    conn.close()
    return len(cases)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    
    logging.info("Starting Classification Worker...")
    empty_streak = 0
    
    while True:
        try:
            count = classify_batch(args.limit)
            if count == 0:
                empty_streak += 1
                if empty_streak > 5:
                    logging.info("No unclassified digests found. Sleeping 30s...")
                    time.sleep(30)
                else:
                    time.sleep(5)
            else:
                empty_streak = 0
                
        except Exception as e:
            logging.error(f"Worker Loop Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
