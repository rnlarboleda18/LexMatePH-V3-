import os
import sqlite3

def check_db(db_path):
    print(f"\nChecking {db_path}...")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        if tables:
            print(f"Found {len(tables)} tables:")
            for table in tables:
                print(f"  - {table[0]}")
                if "const" in table[0].lower() or "codal" in table[0].lower():
                    print(f"    (Potential match: {table[0]})")
        else:
            print("No tables found.")
    except Exception as e:
        print(f"Error accessing database: {e}")

if __name__ == "__main__":
    dbs = [
        r'C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\LexCode\codex_phil.db',
        r'C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\api\questions.db'
    ]
    for db in dbs:
        if os.path.exists(db):
            check_db(db)
        else:
            print(f"\nFile not found: {db}")
