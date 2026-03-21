import sqlite3
import os

DB_FILE = r'C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\api\questions.db'
OUTPUT_FILE = r'C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\doctrinal_cases_full_list.txt'

def export_list():
    if not os.path.exists(DB_FILE):
        print(f"Database not found: {DB_FILE}")
        return

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT Year, Subject, "Case Title" FROM doctrinal_cases ORDER BY Year DESC, Subject ASC')
        rows = cursor.fetchall()
        
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write('FULL DOCTRINAL CASES LIST\n\n')
            for row in rows:
                year = row[0] if row[0] else "N/A"
                subject = row[1] if row[1] else "N/A"
                title = row[2] if row[2] else "N/A"
                f.write(f'{year} | {subject} | {title}\n')
        
        print(f"Successfully exported {len(rows)} cases to {OUTPUT_FILE}")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    export_list()
