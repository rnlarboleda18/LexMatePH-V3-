
import psycopg2
import json
import os

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # data/CodexPhil
DATA_DIR = os.path.dirname(BASE_DIR)

def get_db_connection():
    try:
        settings_path = os.path.join(DATA_DIR, '../../local.settings.json')
        if os.path.exists(settings_path):
            with open(settings_path) as f:
                settings = json.load(f)
                return psycopg2.connect(settings['Values']['DB_CONNECTION_STRING'])
    except:
        pass
    return psycopg2.connect("postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local")

def assess():
    print("--- ASSESSING RPC CONTENT & LINKS ---")
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 1. VERIFY AMENDMENTS (Spot Check)
    print("\n[1] AMENDMENT VERIFICATION")
    # RA 10951 (2017) amended Art 9 fines to P40,000 for light felonies.
    # RA 8353 (1997) reclassified Rape (Art 335 is now 266-A, checking if 335 is repealed or references 266-A)
    
    # Get RPC ID
    cur.execute("SELECT code_id FROM legal_codes WHERE full_name LIKE '%Revised Penal Code%' LIMIT 1")
    res = cur.fetchone()
    if not res:
        print("CRITICAL: Revised Penal Code not found in legal_codes!")
        return
    rpc_id = res[0]
    
    for art in ['9', '315', '335', '266-A']:
        cur.execute("""
            SELECT content, amendment_id, valid_from 
            FROM article_versions 
            WHERE code_id = %s AND article_number = %s 
            ORDER BY valid_from DESC LIMIT 1
        """, (rpc_id, art))
        row = cur.fetchone()
        if row:
            print(f"  Art. {art}:")
            print(f"    - Source: {row[1]}")
            print(f"    - Valid From: {row[2]}")
            print(f"    - Preview: {row[0][:100]}...")
        else:
            print(f"  Art. {art}: NOT FOUND")

    # 2. ASSESS LINKS
    print("\n[2] JURISPRUDENCE LINKS STATUS")
    cur.execute("SELECT COUNT(*) FROM jurisprudence_links")
    link_count = cur.fetchone()[0]
    print(f"  Total Links: {link_count}")
    
    if link_count > 0:
        cur.execute("SELECT * FROM jurisprudence_links LIMIT 3")
        print("  Sample Links:", cur.fetchall())

    # 3. SAMPLE SOURCE DATA
    print("\n[3] SOURCE DATA (sc_decided_cases.statutes_involved)")
    cur.execute("""
        SELECT statutes_involved 
        FROM sc_decided_cases 
        WHERE statutes_involved IS NOT NULL 
          AND statutes_involved::text LIKE '%Revised Penal Code%' 
        LIMIT 3
    """)
    rows = cur.fetchall()
    for i, r in enumerate(rows):
        print(f"  Sample {i+1}: {str(r[0])[:150]}...")

    conn.close()

if __name__ == "__main__":
    assess()
