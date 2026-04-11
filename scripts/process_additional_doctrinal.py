import psycopg2
import re
from datetime import datetime
import csv
import io

# Input Data from User
raw_csv_data = """Case Name,Case Number,Date
Duenas vs. Metrobank,G.R. No. 209463,"Nov 29, 2022"
Republic vs. Espeho,G.R. No. 225722,"April 26, 2023"
Bote vs. Spouses Badar,G.R. No. 236140,"April 19, 2023"
Plana vs. Chua,G.R. No. 2636,"Jan 10, 2023"
Republic vs. Sadka,G.R. No. 218640,"Nov 29, 2021"
Morales vs. De Guia,G.R. No. 247367,"Dec 5, 2022"
Garcia vs. Esclito,G.R. No. 207210,"March 21, 2022"
RVM vs. Republic,G.R. No. 205641,"Oct 5, 2022"
Samson vs. Tapus,G.R. No. 245914,"June 16, 2021"
Republic vs. Heirs of Buok,G.R. No. 207159,"Feb 28, 2022"
Alanis vs. Court of Appeals,G.R. No. 216425,"Nov 11, 2020"
Tan-Andal vs. Andal,G.R. No. 196359,"May 11, 2021"
Padrique-Georfo vs. Republic,G.R. No. 250320,"Jan 17, 2023"
Candelario vs. Candelario,G.R. No. 222068,"July 25, 2023"
People vs. Leonardo,G.R. No. 224410,"June 6, 2018"
San Juan vs. People,G.R. No. 236374,"Feb 1, 2023"
Suleiman vs. Waldo,G.R. No. 255531,"Dec 5, 2022"
Crisologo vs. Sandiganbayan,G.R. No. 244102,"March 1, 2023"
Dangen vs. Lazada Express,G.R. No. 250132,"Jan 17, 2023"
Haugen vs. Omni Shipping,G.R. No. 252431,"Jan 11, 2023"
DPWH vs. Tamparong Jr.,G.R. No. 211516,"March 8, 2023"
Linconn Ong vs. Senate,G.R. No. 257401,"March 28, 2023"
Albano vs. Comelec,G.R. No. 259642,"Feb 7, 2023"
Bayan Muna vs. Arroyo,G.R. No. 182734,"Jan 10, 2023"
Guevarra-Castil vs. Trinidad,A.C. No. 10294,"July 12, 2022"
Villafuerte vs. Tahanlangit,A.C. No. 13619,"Feb 22, 2023"
Saludares vs. Saludares,A.C. No. 10612,"Jan 31, 2023"
Atty. Larry Gadon Case,G.R. No. 261845,"June 27, 2023"
Randy vs. Rosalina,G.R. No. 265147,"March 15, 2023"
People vs. Carlo Diea,G.R. No. 251912,"Feb 13, 2023"
Oligario Toralba vs. People,G.R. No. 255953,"Sept 29, 2021"
Colminar vs. Colminar,G.R. No. 252468,"Aug 30, 2021"
Arida vs. Baluyot,G.R. No. 251817,"June 5, 2023"
Bohol Resort vs. Dunguan,G.R. No. 237859,"April 19, 2023"
Republic vs. Price Corporation,G.R. No. 231500,"Feb 1, 2023"
Odulio vs. Union Bank,G.R. No. 241517,"June 21, 2023"
Quiambao vs. Sombilla,G.R. No. 248165,"June 14, 2023"
Republic vs. Tantoco,G.R. No. 188005,"June 5, 2023"
Zabarte vs. Puyat,G.R. No. 200376,"April 12, 2023"
BCDA vs. CIR,G.R. No. 217894,"Nov 7, 2018"
Maricalum Mining vs. Florentino,G.R. No. 221813,"July 23, 2018"
Amoroso vs. Vantage Drill Int'l,G.R. No. 253011,"April 12, 2023"
Ago Realty vs. Dr. Angelina Go,G.R. No. 210906,"Oct 16, 2019"
Zuneca vs. Natrapharm,G.R. No. 211850,"Sept 8, 2020"
Kossac vs. FILSCAP,G.R. No. 222510,"Jan 11, 2023"
Anrey vs. FILSCAP,G.R. No. 254325,"Sept 14, 2022"
Henson vs. UCPB Gen. Insurance,G.R. No. 223134,"Aug 14, 2019"
CIR vs. COMELEC,G.R. No. 244155,"May 11, 2021"
People vs. Mendez,G.R. No. 208310,"March 28, 2023"
CIR vs. Unioil,G.R. No. 204405,"Aug 4, 2021"
CIR vs. Toledo Power Co.,G.R. No. 238260,"June 21, 2023"
"""

PG_CONNECTION_STRING = "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

def normalize_title_token(text):
    if not text: return set()
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text.lower())
    tokens = set(text.split())
    stop_words = {"v", "vs", "the", "of", "and", "in", "re", "no", "gr", "l", "people", "case", "name", "number", "date"}
    return tokens - stop_words

def parse_date(date_str):
    if not date_str: return None
    formats = ["%b %d, %Y", "%B %d, %Y", "%b. %d, %Y", "%B %d, %Y"] # Handle "Sept" special case later
    
    # Fix "Sept" -> "Sep" etc
    date_str = date_str.replace("Sept ", "Sep ").replace("April", "Apr").replace("March", "Mar")
    
    # Try parsing
    try:
        return datetime.strptime(date_str, "%b %d, %Y").date()
    except:
        try:
             return datetime.strptime(date_str, "%B %d, %Y").date()
        except:
            return None

def main():
    pg_conn = psycopg2.connect(PG_CONNECTION_STRING)
    pg_cur = pg_conn.cursor()
    
    input_rows = []
    # Use csv reader to handle quotes
    csv_file = io.StringIO(raw_csv_data)
    reader = csv.reader(csv_file)
    
    for row in reader:
        if not row or row[0].startswith("Case Name"): continue
        if len(row) < 3: continue
        input_rows.append(row)
        
    print(f"Processing {len(input_rows)} additional cases...")
    
    found_count = 0
    missing_items = []
    
    for row in input_rows:
        title, case_num, date_str = row
        
        # Extract digits from case number
        digits = re.findall(r'\d+', case_num)
        main_digits = digits[0] if digits else None
        
        # Parse date
        dt = parse_date(date_str)
        
        match_found = None
        match_reason = ""
        
        # 1. Search by Digits
        if main_digits and len(main_digits) > 2:
            pg_cur.execute("SELECT id, case_number, title, date FROM sc_decided_cases WHERE case_number LIKE %s", (f"%{main_digits}%",))
            candidates = pg_cur.fetchall()
            
            for cand in candidates:
                cand_id, cand_num, cand_title, cand_date = cand
                # Check title similarity as confirmation if multiple results
                # Or if exact digit match (some might be partial e.g. 123 in 12345)
                
                # If candidate date matches, it's a slam dunk
                if dt and cand_date and cand_date == dt:
                    match_found = cand
                    match_reason = f"Digits + Date Match ({main_digits}, {dt})"
                    break
                
                # If title overlaps significantly
                tok_in = normalize_title_token(title)
                tok_cand = normalize_title_token(cand_title)
                if len(tok_cand.intersection(tok_in)) >= min(len(tok_in), 2): # At least 2 words or all words match
                     match_found = cand
                     match_reason = f"Digits + Title Match ({main_digits})"
                     break
            
            # If no strict match but only one candidate has those digits and it looks 'close enough' (digit is unique-ish)
            if not match_found and len(candidates) == 1:
                 # Check digits again strictly to ensure we didn't match "123" inside "91234"
                 cand_digits = re.findall(r'\d+', candidates[0][1])
                 if main_digits in cand_digits:
                     match_found = candidates[0]
                     match_reason = f"Unique Digit Match ({main_digits})"

        # 2. Search by Date (if no digit match)
        if not match_found and dt:
             pg_cur.execute("SELECT id, case_number, title, date FROM sc_decided_cases WHERE date = %s", (dt,))
             candidates = pg_cur.fetchall()
             
             tok_in = normalize_title_token(title)
             best_overlap = 0
             
             for cand in candidates:
                 tok_cand = normalize_title_token(cand[2])
                 overlap = len(tok_cand.intersection(tok_in))
                 if overlap > best_overlap:
                     best_overlap = overlap
                     if overlap >= 1: # At least one significant word matches
                         match_found = cand
                         match_reason = f"Date + Title Match ({dt})"

        # 3. Fuzzy Title Search (Last Resort)
        if not match_found:
             toks = list(normalize_title_token(title))
             longest_word = max(toks, key=len) if toks else ""
             if len(longest_word) > 4:
                 pg_cur.execute("SELECT id, case_number, title, date FROM sc_decided_cases WHERE title ILIKE %s LIMIT 5", (f"%{longest_word}%",))
                 candidates = pg_cur.fetchall()
                 for cand in candidates:
                     tok_cand = normalize_title_token(cand[2])
                     overlap = len(tok_cand.intersection(set(toks)))
                     if overlap >= len(toks) * 0.6: # 60% match
                          match_found = cand
                          match_reason = f"Title Fuzzy ({longest_word})"
                          break

        if match_found:
            print(f"[FOUND] {title} -> ID {match_found[0]} [{match_reason}]")
            pg_cur.execute("UPDATE sc_decided_cases SET is_doctrinal = TRUE WHERE id = %s", (match_found[0],))
            found_count += 1
        else:
            print(f"[MISSING] {title} ({case_num}, {date_str})")
            missing_items.append(f"{title}  ({case_num}, {date_str})")

    pg_conn.commit()
    
    # Append to existing missing list file
    with open('final_missing_doctrinal.txt', 'a', encoding='utf-8') as f:
        if missing_items:
            f.write("\n--- Additional Missing Cases ---\n")
            for item in missing_items:
                f.write(f"{item}\n")

    print(f"\n--- PROCESSING COMPLETE ---")
    print(f"Found & Updated: {found_count}")
    print(f"Missing: {len(missing_items)}")
    
    pg_conn.close()

if __name__ == "__main__":
    main()
