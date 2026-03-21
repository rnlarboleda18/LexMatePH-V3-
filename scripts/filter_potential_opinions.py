import psycopg2
import json

def run():
    conn_str = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor()
    
    # 1. Get the IDs from the file (or re-query to be safe/faster if reading file is slow, but file is fine)
    # Re-querying is robust.
    
    query = """
        SELECT id, full_text_md, short_title
        FROM sc_decided_cases
        WHERE division ILIKE '%En Banc%'
          AND (separate_opinions IS NULL OR separate_opinions::text = '[]' OR separate_opinions::text = 'null')
    """
    
    # Optimized: We can do the text search in SQL for speed
    # But python allows more complex regex if needed. SQL ILIKE is fast enough for 23k.
    
    print("Querying and filtering in DB...")
    filter_sql = """
        SELECT id, short_title, LENGTH(full_text_md)
        FROM sc_decided_cases
        WHERE division ILIKE '%En Banc%'
          AND (separate_opinions IS NULL OR separate_opinions::text = '[]' OR separate_opinions::text = 'null')
          AND (
             full_text_md ILIKE '%Separate Opinion%' OR
             full_text_md ILIKE '%Concurring Opinion%' OR
             full_text_md ILIKE '%Dissenting Opinion%' OR
             full_text_md ILIKE '%Concurring and Dissenting%'
          )
        ORDER BY LENGTH(full_text_md) DESC
    """
    
    cur.execute(filter_sql)
    rows = cur.fetchall()
    
    print(f"\n--- POTENTIAL MISSING OPINIONS (En Banc) ---")
    print(f"Total Matches: {len(rows)}")
    
    if len(rows) > 0:
        print("\nTop 10 Largest Candidates:")
        for r in rows[:10]:
            print(f"ID {r[0]} | {r[2]:,} chars | {r[1]}")
            
    ids = [str(r[0]) for r in rows]
    outfile = "missing_opinion_candidates.txt"
    with open(outfile, 'w') as f:
        f.write(",".join(ids))
        
    print(f"\nSaved {len(ids)} IDs to {outfile}")
    conn.close()

if __name__ == "__main__":
    run()
