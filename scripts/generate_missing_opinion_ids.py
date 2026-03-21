import psycopg2

def run():
    conn_str = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor()
    
    print("Generating ID list for En Banc Missing Opinions (Loose Filter)...")
    
    query = """
        SELECT id
        FROM sc_decided_cases
        WHERE division ILIKE '%En Banc%'
          AND (separate_opinions IS NULL OR separate_opinions::text = '[]' OR separate_opinions::text = 'null')
          AND (
             full_text_md ILIKE '%CONCURRING%' OR
             full_text_md ILIKE '%DISSENTING%' OR
             full_text_md ILIKE '%SEPARATE%' 
          )
        ORDER BY LENGTH(full_text_md) DESC
    """
    
    cur.execute(query)
    rows = cur.fetchall()
    
    ids = [str(r[0]) for r in rows]
    outfile = "missing_opinion_ids.txt"
    
    with open(outfile, 'w') as f:
        f.write(",".join(ids))
        
    print(f"Total Found: {len(ids)}")
    print(f"Saved to {outfile}")
    conn.close()

if __name__ == "__main__":
    run()
