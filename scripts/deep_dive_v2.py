import psycopg2
import re
from datetime import datetime, timedelta
import os

PG_CONNECTION_STRING = "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

def normalize(text):
    return re.sub(r'[^a-zA-Z0-9]', '', text).lower()

def extract_parties(title):
    # Split by " v. ", " vs. ", " vs "
    parts = re.split(r'\s+v\.?s?\.?\s+', title, flags=re.IGNORECASE)
    cleaned_parts = []
    ignore_words = {"people", "philippines", "republic", "director", "court", "appeals", "ca", "nlrc", "cir", "comelec", "commission", "secretary", "executive"}
    
    for p in parts:
        # Get significant words
        words = re.findall(r'[a-zA-Z]{4,}', p)
        for w in words:
            if w.lower() not in ignore_words:
                cleaned_parts.append(w)
    return cleaned_parts

def parse_date(date_str):
    if not date_str: return None
    date_str = date_str.replace("Sept ", "Sep ").replace("April", "Apr").replace("March", "Mar")
    formats = ["%b %d, %Y", "%B %d, %Y", "%Y-%m-%d"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except:
             continue
    return None

def main():
    pg_conn = psycopg2.connect(PG_CONNECTION_STRING)
    pg_cur = pg_conn.cursor()

    # Read the missing file
    lines = []
    if os.path.exists('final_missing_doctrinal.txt'):
        with open('final_missing_doctrinal.txt', 'r', encoding='utf-8') as f:
            lines = [l.strip() for l in f.readlines() if l.strip() and not l.startswith("---")]
    
    print(f"Deep Dive V2 processing {len(lines)} missing cases...")
    
    found_count = 0
    still_missing = []
    
    for line in lines:
        try:
            # Parse line: "Title (GR No..., Date)"
            if '(' not in line: 
                still_missing.append(line)
                continue
                
            title_part = line.split('(')[0].strip()
            meta_part = line.split('(')[1].strip()
            
            # Extract Date
            date_match = re.search(r'([A-Za-z]+\.?\s+\d{1,2},?\s+\d{4})', meta_part)
            if not date_match:
                 # Try rigid format
                 date_match = re.search(r'(\d{4}-\d{2}-\d{2})', meta_part)
            
            date_val = parse_date(date_match.group(1)) if date_match else None
            
            # Extract Digits
            digits = re.findall(r'\d+', meta_part)
            # Filter out year (if date found)
            clean_digits = []
            if date_val:
                year_str = str(date_val.year)
                clean_digits = [d for d in digits if d != year_str and d not in str(date_val)]
            else:
                clean_digits = [d for d in digits if len(d) > 3] # Guess
            
            main_digit = clean_digits[0] if clean_digits else None

            match_found = None
            match_reason = ""

            # STRATEGY 1: SEARCH BY UNIQUE DIGIT SEQUENCE (Robust)
            if main_digit and len(main_digit) >= 4:
                # Search anywhere in case_number
                pg_cur.execute("SELECT id, case_number, title, date FROM sc_decided_cases WHERE case_number LIKE %s", (f"%{main_digit}%",))
                candidates = pg_cur.fetchall()
                if candidates:
                    # Filter
                    for cand in candidates:
                         # 1A. Confirm Date Match (Loose)
                         if date_val and cand[3]:
                             delta = abs((cand[3] - date_val).days)
                             if delta <= 10: # Allow 10 days diff
                                 match_found = cand
                                 match_reason = f"Digit ({main_digit}) + Date (+/- {delta} days)"
                                 break
                         
                         # 1B. Title Overlap
                         cand_title_norm = normalize(cand[2])
                         title_part_norm = normalize(title_part)
                         if title_part_norm[:10] in cand_title_norm:
                                 match_found = cand
                                 match_reason = f"Digit ({main_digit}) + Title Start"
                                 break
                    
                    # 1C. If still no match but only 1 candidate, trust the digit if it's long enough
                    if not match_found and len(candidates) == 1 and len(main_digit) >= 5:
                         match_found = candidates[0]
                         match_reason = f"Unique Long Digit ({main_digit})"

            # STRATEGY 2: SEARCH BY PARTY NAME + DATE RANGE (No digits needed)
            if not match_found and date_val:
                parties = extract_parties(title_part)
                for party in parties:
                    if len(party) < 4: continue # Skip short words
                    
                    # Search DB for cases within +/- 30 days having this party name
                    d_start = date_val - timedelta(days=30)
                    d_end = date_val + timedelta(days=30)
                    pg_cur.execute(
                        "SELECT id, case_number, title, date FROM sc_decided_cases WHERE date >= %s AND date <= %s AND title ILIKE %s", 
                        (d_start, d_end, f"%{party}%")
                    )
                    candidates = pg_cur.fetchall()
                    
                    if candidates:
                        # Find best match
                        match_found = candidates[0] # Take first for now, usually unique
                        match_reason = f"Party ({party}) + Date Window"
                        break
            
            # STRATEGY 3: ADMINISTRATIVE CASE HANDLING
            if not match_found:
                 if "A.C." in meta_part or "A.M." in meta_part or "B.M." in meta_part:
                     # Search for "AC <digit>" or "AC-<digit>"
                     if main_digit:
                         pg_cur.execute("SELECT id, case_number, title, date FROM sc_decided_cases WHERE case_number ILIKE %s OR case_number ILIKE %s", (f"%{main_digit}%", f"%AC%{main_digit}%"))
                         candidates = pg_cur.fetchall()
                         for cand in candidates:
                             # Check title
                             tok_in = set(extract_parties(title_part))
                             tok_cand = set(extract_parties(cand[2]))
                             if tok_in.intersection(tok_cand):
                                 match_found = cand
                                 match_reason = "Admin Number + Party Match"
                                 break

            if match_found:
                print(f"[FOUND] {title_part[:40]}... -> ID {match_found[0]} [{match_reason}] - ({match_found[2][:40]})")
                pg_cur.execute("UPDATE sc_decided_cases SET is_doctrinal = TRUE WHERE id = %s", (match_found[0],))
                found_count += 1
            else:
                print(f"[FAILED] {line[:60]}...")
                still_missing.append(line)
        except Exception as e:
            print(f"Error processing {line[:30]}: {e}")
            still_missing.append(line)

    pg_conn.commit()
    print(f"\n--- V2 COMPLETE ---")
    print(f"Recovered: {found_count}")
    print(f"Final Missing: {len(still_missing)}")
    
    with open('final_missing_v2.txt', 'w', encoding='utf-8') as f:
         f.write(f"--- V2 Missing ({len(still_missing)}) ---\n")
         for m in still_missing:
             f.write(f"{m}\n")
             
    pg_conn.close()

if __name__ == "__main__":
    main()
