import psycopg2
from psycopg2.extras import RealDictCursor

def attach_link_counts(cur, articles):
    if not articles:
        return

    article_nums = [str(a['article_num']) for a in articles]
    print(f"Total articles to inspect: {len(article_nums)}")

    # Query exactly as phrased in roc.py
    query = """
        SELECT provision_id, target_paragraph_index, COUNT(*) as link_count
        FROM codal_case_links 
        WHERE statute_id = 'ROC' 
          AND provision_id = ANY(%s)
          AND target_paragraph_index IS NOT NULL
        GROUP BY provision_id, target_paragraph_index
        ORDER BY provision_id, target_paragraph_index
    """
    
    cur.execute(query, (article_nums,))
    rows = cur.fetchall()
    print(f"Total rows aggregates fetched: {len(rows)}")
    
    link_map = {}
    for r in rows:
        art = r['provision_id']
        idx = r['target_paragraph_index']
        count = r['link_count']
        
        if art not in link_map:
            link_map[art] = {}
        link_map[art][idx] = count
        
    match_count = 0
    for art in articles:
        anum = str(art['article_num'])
        if anum in link_map:
            match_count += 1
            
    print(f"Total matches in link_map: {match_count}")
    return link_map

def main():
    try:
        conn = psycopg2.connect("postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db")
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT * FROM roc_codal")
        results = cur.fetchall()
        
        link_map = attach_link_counts(cur, results)
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
