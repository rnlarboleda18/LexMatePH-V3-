import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor

def get_conn_str():
    try:
        with open('api/local.settings.json', 'r') as f:
            config = json.load(f)
            return config.get('Values', {}).get('DB_CONNECTION_STRING')
    except Exception: pass
    return None

def test_logic():
    conn_str = get_conn_str()
    if not conn_str: return
    
    try:
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Load all CONST rows ordered by list_order
        cur.execute("""
            SELECT id, list_order, article_num, article_label, section_label, content_md 
            FROM const_codal 
            WHERE book_code = 'CONST'
            ORDER BY list_order ASC 
        """)
        rows = cur.fetchall()
        
        # Convert to list of dict for modification
        items = [dict(r) for r in rows]
        
        new_items = []
        current_group = None
        current_article = None
        
        for item in items:
            article_num = item['article_num']
            section_label = item['section_label'] or ""
            content = item['content_md'] or ""
            
            # 1. Reset group on new Article
            if item['article_label'] != current_article:
                current_article = item['article_label']
                current_group = None
                
            # Heuristic: Insert "State Policies" before Section 7 in Article II
            if item['article_label'] == 'ARTICLE II' and section_label == 'SECTION 7.':
                # Insert the header row
                header_row = {
                    'id': -1, # Dummy ID
                    'list_order': item['list_order'], # Will be inserted here
                    'article_num': 'II-STATE-POLICIES',
                    'article_label': 'ARTICLE II',
                    'section_label': 'ARTICLE II', # Duplicates article label for sub-headers
                    'content_md': '### State Policies'
                }
                new_items.append(header_row)
                current_group = 'State Policies' # Update group
                
            # 2. Check for subheaders starting with '###'
            if content.startswith('###'):
                 # It's a sub-header row!
                 current_group = content.replace('###', '').strip()
                 # We don't populate group_header for the sub-header row itself usually in DB
                 item['group_header'] = None
                 new_items.append(item)
                 continue
                 
            # 3. Populate group_header for regular rows
            item['group_header'] = current_group
            new_items.append(item)
            
        # Re-assign list_order starting from 1 to verify sequence
        for i, item in enumerate(new_items):
            item['list_order'] = i + 1
            
        # Write results to file
        with open('test_const_grouping_result.txt', 'w', encoding='utf-8') as f:
            for item in new_items:
                f.write(f"Ord: {item['list_order']} | Num: {item['article_num']} | Lbl: {item['article_label']} | Sec: {item['section_label']} | Grp: {item.get('group_header')}\n")
                if item['content_md'].startswith('###'):
                    f.write(f"  Subheader: {item['content_md']}\n")
                f.write("-" * 40 + "\n")
                
        print(f"Results written to test_const_grouping_result.txt. Processed {len(new_items)} items.")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_logic()
