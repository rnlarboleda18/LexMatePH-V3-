import psycopg2
from psycopg2.extras import RealDictCursor
import json

DB_CONNECTION = "dbname=lexmateph-ea-db user=postgres password=b66398241bfe483ba5b20ca5356a87be host=localhost port=5432"

def simulate_api():
    try:
        conn = psycopg2.connect(DB_CONNECTION)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        print("Executing query...")
        cur.execute("""
            SELECT * FROM consti_codal 
            WHERE book_code IS NULL OR book_code = 'CONST'
            ORDER BY list_order ASC 
        """)
        results = cur.fetchall()
        print(f"Fetched {len(results)} rows.")
        
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
             new_r['article_title'] = "" 
             new_r['title_label'] = title_label            
             new_r['group_header'] = r.get('group_header') 
             new_r['section_label'] = None                 
             
             mapped_results.append(new_r)
        
        print(f"Successfully mapped {len(mapped_results)} articles.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    simulate_api()
