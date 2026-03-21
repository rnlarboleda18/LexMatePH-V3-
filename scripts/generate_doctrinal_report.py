import sqlite3
import os

def generate_doctrinal_report():
    db_path = 'api/questions.db'
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    query = 'SELECT "Case Title", Year FROM doctrinal_cases ORDER BY Year DESC, "Case Title" ASC'
    
    try:
        cur.execute(query)
        rows = cur.fetchall()
        
        print("# Full Doctrinal Cases List (SQLite)")
        print(f"\n**Total Cases**: {len(rows)}\n")
        
        current_year = None
        for r in rows:
            title = r[0]
            year = r[1]
            
            if year != current_year:
                current_year = year
                print(f"\n## {current_year}")
            
            # Simple list
            print(f"- {title}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    generate_doctrinal_report()
