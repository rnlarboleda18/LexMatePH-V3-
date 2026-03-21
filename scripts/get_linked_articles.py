import psycopg2

def main():
    try:
        conn = psycopg2.connect("postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local")
        cur = conn.cursor()
        
        # Get distinct provision_ids which HAVE links (where value is not -1 is better as well)
        cur.execute("""
            SELECT DISTINCT provision_id, target_paragraph_index 
            FROM codal_case_links 
            WHERE statute_id = 'ROC' AND provision_id LIKE 'Rule %%' 
              AND target_paragraph_index IS NOT NULL
            LIMIT 10
        """)
        rows = cur.fetchall()
        print("--- Linked ROC Provisions (With Indices) ---")
        for r in rows:
            print(f"Provision: {r[0]} | Paragraph Index: {r[1]}")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
