import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONNECTION = "dbname=bar_reviewer_local user=postgres password=b66398241bfe483ba5b20ca5356a87be host=localhost port=5432"

def attach_link_counts(cur, articles):
    if not articles:
        return

    key_ids = [str(a.get('key_id') or a['article_num']) for a in articles]
    
    query = """
        SELECT provision_id, target_paragraph_index, COUNT(*) as link_count
        FROM codal_case_links 
        WHERE statute_id = 'CONST' 
          AND provision_id = ANY(%s)
          AND target_paragraph_index IS NOT NULL
        GROUP BY provision_id, target_paragraph_index
        ORDER BY provision_id, target_paragraph_index
    """
    
    cur.execute(query, (key_ids,))
    rows = cur.fetchall()

def test_api_full():
    try:
        conn = psycopg2.connect(DB_CONNECTION)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT * FROM consti_codal 
            WHERE book_code IS NULL OR book_code = 'CONST'
            ORDER BY list_order ASC 
        """)
        results = cur.fetchall()
        
        mapped_results = []
        for r in results:
             new_r = dict(r)
             a_label = r['article_label'] or ""
             title = r['article_title'] or ""
             s_label = r['section_label'] or ""
             
             title_label = None
             if a_label:
                 title_label = a_label
                 if title and title.upper() != a_label.upper():
                     title_label = f"{a_label}\n{title}"
             
             if "PREAMBLE" in a_label.upper():
                 title_label = "PREAMBLE"
                 article_num = ""
             elif s_label:
                 article_num = s_label.rstrip('.')
             else:
                 article_num = ""

             new_r['key_id'] = str(r['article_num'])  
             new_r['article_num'] = article_num 
             new_r['title_label'] = title_label            
             mapped_results.append(new_r)
        
        print("Calling attach_link_counts...")
        attach_link_counts(cur, mapped_results)
        print("Success!")
        
        cur.close()
        conn.close()
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_api_full()
