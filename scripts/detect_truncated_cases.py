import psycopg2
import os

def detect_truncated():
    conn_str = os.environ.get("DB_CONNECTION_STRING") or "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"
    try:
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor()
        
        # Select digested cases
        cur.execute("""
            SELECT id, case_number, title, LENGTH(raw_content), raw_content 
            FROM supreme_decisions 
            WHERE digest_facts IS NOT NULL
        """)
        
        rows = cur.fetchall()
        print(f"Analyzing {len(rows)} digested cases...")
        
        truncated_candidates = []
        
        for row in rows:
            cid, cnum, title, length, content = row
            
            # Criteria 1: Suspiciously Short
            if length < 3000: 
                truncated_candidates.append((cid, cnum, "Very Short (<3000 chars)"))
                continue
                
            # Criteria 2: Missing Standard Endings (Checking last interpretation)
            # Standard endings: "SO ORDERED", "WHEREFORE", "denied", "granted"
            # We'll check the last 500 chars.
            last_part = content[-1000:].lower()
            
            has_ending = any(x in last_part for x in ['so ordered', 'wherefore', 'accordingly', 'petition is', 'decision is', 'judgment is'])
            
            if not has_ending:
                truncated_candidates.append((cid, cnum, "Missing standard ending phrase"))
        
        print("\nPotential Truncated Cases:")
        if not truncated_candidates:
            print("None found based on heuristics.")
        else:
            print(f"Found {len(truncated_candidates)} candidates:")
            for cid, cnum, reason in truncated_candidates:
                print(f"ID: {cid} | {cnum} | Reason: {reason}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    detect_truncated()
