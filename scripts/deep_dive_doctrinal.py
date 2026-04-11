import sqlite3
import psycopg2
import re
import os
from datetime import datetime, timedelta

SQLITE_DB_PATH = "api/questions.db"
PG_CONNECTION_STRING = "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

def normalize_title_token(text):
    if not text: return ""
    # "Province of Sulu v. Executive Secretary" -> {"province", "sulu", "executive"}
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text.lower())
    tokens = set(text.split())
    # Remove stop words
    stop_words = {"v", "vs", "the", "of", "and", "in", "re", "no", "gr", "l", "people"}
    return tokens - stop_words

def extract_metadata(row_str):
    # Format: "Title (G.R. No. 12345, Jan 1, 2020)"
    # Or: "Title (A.C. No. 12345, Jan 1, 2020)"
    
    # Extract Date
    date_match = re.search(r'([A-Za-z]+\.?\s+\d{1,2},?\s+\d{4})\)', row_str)
    date_str = date_match.group(1) if date_match else None
    
    # Extract Number (digits only)
    # Look for "No. <digits>" or "G.R. <digits>"
    digits = re.findall(r'\d+', row_str)
    # Usually the GR number is the first big number, year is last
    # Heuristic: Take the longest number that isn't the year
    gr_candidate = None
    for d in digits:
        if len(d) >= 4 and d != date_str: # Avoid matching the year in date
            if date_str and str(d) in date_str: continue 
            gr_candidate = d
            break
            
    # Extract Title
    title_part = row_str.split('(')[0].strip()
    
    return title_part, gr_candidate, date_str

def main():
    try:
        # Load Missing List
        with open('missing_doctrinal.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        pg_conn = psycopg2.connect(PG_CONNECTION_STRING)
        pg_cur = pg_conn.cursor()

        print(f"--- DEEP DIVE ON {len(lines)-3} MISSING CASES ---")
        
        found_matches = []
        still_missing = []

        for line in lines:
            if line.startswith("---") or not line.strip(): continue
            
            line = line.strip()
            title, gr_digits, date_str = extract_metadata(line)
            
            match_found = None
            match_reason = ""
            
            # METHOD 1: Search by Digits in case_number (Likeliest for formatting mismatches)
            if gr_digits and len(gr_digits) > 3:
                pg_cur.execute("SELECT id, case_number, title, date FROM sc_decided_cases WHERE case_number LIKE %s", (f"%{gr_digits}%",))
                candidates = pg_cur.fetchall()
                if candidates:
                    # Filter candidates
                    for cand in candidates:
                        # If simple match found
                        match_found = cand
                        match_reason = f"Digits Match ({gr_digits})"
                        break
            
            # METHOD 2: Search by Date (Power Move)
            if not match_found and date_str:
                try:
                    dt = datetime.strptime(date_str.replace(".", ""), "%b %d %Y").date()
                    # Range search +/- 0 days (exact date)
                    pg_cur.execute("SELECT id, case_number, title, date FROM sc_decided_cases WHERE date = %s", (dt,))
                    candidates = pg_cur.fetchall()
                    
                    if candidates:
                        # Tie breaker: Title Similarity
                        best_score = 0
                        target_tokens = normalize_title_token(title)
                        
                        for cand in candidates:
                            cand_title = cand[2]
                            cand_tokens = normalize_title_token(cand_title)
                            overlap = len(target_tokens.intersection(cand_tokens))
                            
                            if overlap > best_score:
                                best_score = overlap
                                match_found = cand
                                match_reason = f"Date Match + Title Overlap ({overlap})"
                            
                            # If only 1 candidate on that date, take it (carefully)
                            if len(candidates) == 1 and overlap >= 0:
                                match_found = candidates[0]
                                match_reason = "Date Match (Single Result)"
                                
                except Exception as e:
                    # Date parsing failed
                    pass

            # METHOD 3: Full Text Search on Title (Last Resort)
            if not match_found:
               # Simple ILIKE on first big word
               tokens = list(normalize_title_token(title))
               if tokens:
                   big_word = max(tokens, key=len)
                   if len(big_word) > 4:
                       pg_cur.execute("SELECT id, case_number, title, date FROM sc_decided_cases WHERE title ILIKE %s LIMIT 5", (f"%{big_word}%",))
                       candidates = pg_cur.fetchall()
                       # Manual verify needed here usually, but let's automate a strict check
                       for cand in candidates:
                           cand_tokens = normalize_title_token(cand[2])
                           target_tokens = normalize_title_token(title)
                           if len(target_tokens.intersection(cand_tokens)) >= len(target_tokens) * 0.5:
                               match_found = cand
                               match_reason = f"Title Fuzz ({big_word})"
                               break

            # RECORD RESULT
            if match_found:
                print(f"[FOUND] {title[:30]}... -> ID {match_found[0]} ({match_found[1]}) [{match_reason}]")
                found_matches.append(match_found[0])
                # Update DB immediately
                pg_cur.execute("UPDATE sc_decided_cases SET is_doctrinal = TRUE WHERE id = %s", (match_found[0],))
            else:
                print(f"[STILL MISSING] {title[:30]}... (GR: {gr_digits}, Date: {date_str})")
                still_missing.append(line)

        if still_missing:
            print(f"\nWriting {len(still_missing)} remaining missing cases to 'final_missing_doctrinal.txt'...")
            with open('final_missing_doctrinal.txt', 'w', encoding='utf-8') as f:
                f.write(f"--- Final Missing Doctrinal Cases ({len(still_missing)}) ---\n")
                for m in still_missing:
                    f.write(f"{m}\n")
        
        pg_conn.close()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
