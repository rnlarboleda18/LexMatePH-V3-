import sqlite3

def scan_db(db_name):
    print(f"\n--- Scanning {db_name} ---")
    try:
        conn = sqlite3.connect(db_name)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [t[0] for t in c.fetchall()]
        
        print("Tables:", tables)
        for t in tables:
            c.execute(f"PRAGMA table_info('{t}')")
            cols = c.fetchall()
            print(f"Schema for {t}: {[col[1] for col in cols]}")
        conn.close()
    except Exception as e:
        print(f"Error scanning {db_name}: {e}")

if __name__ == "__main__":
    for db in ['bar_project.db', 'LexCode/codex_phil.db', 'api/questions.db']:
        scan_db(db)
