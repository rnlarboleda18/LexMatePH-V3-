import psycopg2
import re
import os
import logging

# Configuration
DB_CONNECTION_STRING = "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_db_connection():
    return psycopg2.connect(DB_CONNECTION_STRING)

def clean_party_name(name):
    name = name.strip()
    role_pattern = r",\s*(Petitioner|Respondent|Appellant|Appellee|Accused|Plaintiff|Defendant|et al\.|et al)[s\.,]*$"
    name = re.sub(role_pattern, "", name, flags=re.IGNORECASE).strip()
    
    if "people of the philippines" in name.lower(): return "People"
    if "republic of the philippines" in name.lower(): return "Republic"
        
    keywords = ["commissioner", "commission", "corporation", "inc.", "corp.", "bank", "company", "university", "school", "union", "association", "republic", "people", "united", "city", "municipality", "province", "administration", "senate", "house", "congress", "office", "court", "tribunal", "board", "bureau", "agency", "department"]
    for k in keywords:
        # distinct word match
        if re.search(r'\b' + re.escape(k) + r'\b', name, re.IGNORECASE):
             return name 
    
    # Check for list of parties (comma separated)
    if "," in name:
        first_part = name.split(",")[0].strip()
        if first_part and len(first_part.split()) < 5: 
            name = first_part

    tokens = name.split()
    if not tokens: return name
    if len(tokens) == 1: return tokens[0]
    
    last = tokens[-1]
    second_last = tokens[-2].lower() if len(tokens) > 1 else ""
    third_last = tokens[-3].lower() if len(tokens) > 2 else ""
    
    if second_last in ['dela', 'del', 'de', 'di', 'van', 'von', 'san', 'st.', 'sta.']:
        return f"{tokens[-2]} {last}"
    elif third_last in ['de', 'la'] and second_last in ['la', 'del']:
         return f"{tokens[-3]} {tokens[-2]} {last}"
         
    return last

def generate_strict_short_title(full_title):
    if not full_title: return ""

    clean_title = full_title
    clean_title = re.sub(r'^\[?G\.?R\.?.*\]\s*', '', clean_title).strip()
    
    if " - " in clean_title:
        parts = clean_title.split(" - ", 1)
        if parts[0].strip().startswith(("G.R.", "A.M.", "A.C.", "B.M.", "I.P.I.")):
             clean_title = parts[1]

    # Special Case: Accused without People
    if "ACCUSED" in clean_title.upper() and "PEOPLE" not in clean_title.upper():
         clean_accused = clean_party_name(clean_title)
         return f"People v. {clean_accused}"

    separator = None
    if " v. " in clean_title: separator = " v. "
    elif " vs. " in clean_title: separator = " vs. "
    elif " VS. " in clean_title: separator = " VS. "
    elif " V. " in clean_title: separator = " V. "
    elif " versus " in clean_title.lower(): separator = " versus " 
    
    if separator:
        parties = clean_title.split(separator)
        if len(parties) >= 2: 
            p_a = re.split(r'\s+(?:and|AND|&)\s+|,\s+', parties[0])[0].strip()
            p_b = re.split(r'\s+(?:and|AND|&)\s+|,\s+', parties[1])[0].strip()
            
            short_a = clean_party_name(p_a)
            short_b = clean_party_name(p_b)
            return f"{short_a} v. {short_b}"

    if clean_title.lower().startswith(("in re:", "re:", "in the matter of")):
        if clean_title.lower().startswith("in the matter of"):
             clean_title = clean_title.replace("In the matter of", "In re:", 1)
             clean_title = clean_title.replace("IN THE MATTER OF", "In re:", 1)
        return clean_title.split(",")[0].strip()

    role_match = re.search(r",\s*(PETITIONER|RESPONDENT|ACCUSED|PLAINTIFF|DEFENDANT)[S\.,]*$", clean_title, re.IGNORECASE)
    if role_match:
        name_part = clean_title[:role_match.start()].strip()
        return clean_party_name(name_part)
        
    pet_match = re.search(r"([\w\s\.,&]+)(?:,|and)?\s+PETITIONER[S]?\.?", clean_title, re.IGNORECASE)
    resp_match = re.search(r"([\w\s\.,&]+)(?:,|and)?\s+RESPONDENT[S]?\.?", clean_title, re.IGNORECASE)
    
    if pet_match and resp_match:
        p_name = clean_party_name(pet_match.group(1).split(" and ")[0].split(",")[0])
        r_name = clean_party_name(resp_match.group(1).split(" and ")[0].split(",")[0])
        if len(p_name) > 2 and len(r_name) > 2 and p_name != r_name:
             return f"{p_name} v. {r_name}"

    return clean_party_name(clean_title)

def fix_latest_first():
    conn = get_db_connection()
    cur = conn.cursor()
    
    logging.info("Fetching all decisions (Latest First)...")
    cur.execute("SELECT id, title FROM supreme_decisions ORDER BY id DESC")
    # Fetch in blocks to start processing immediately without loading all into RAM if huge? 
    # Actually fetchall is fine for 50k rows.
    rows = cur.fetchall()
    
    logging.info(f"Processing {len(rows)} decisions...")
    
    updates = []
    
    for row in rows:
        did, title = row
        new_short = generate_strict_short_title(title)
        if new_short and new_short != title:
            updates.append((new_short, did))
            
    logging.info(f"Updating {len(updates)} records...")
    
    # Batch update
    batch_size = 1000
    for i in range(0, len(updates), batch_size):
        batch = updates[i:i+batch_size]
        cur.executemany("UPDATE supreme_decisions SET short_title = %s WHERE id = %s", batch)
        conn.commit()
        logging.info(f"Updated batch {i} - {i+len(batch)}")
        
    conn.close()
    logging.info("Done.")

if __name__ == "__main__":
    fix_latest_first()
