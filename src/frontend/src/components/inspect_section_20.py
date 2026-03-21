import sqlite3

db_path = r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\CodexPhil\codex_phil.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print(f"Tables: {tables}")

# Get columns of const_codal
cursor.execute("PRAGMA table_info(const_codal);")
columns = cursor.fetchall()
print(f"Columns in const_codal: {[c[1] for c in columns]}")

# Search for Section 20 content
query = "SELECT * FROM const_codal WHERE content LIKE '%Within its territorial jurisdiction%';"
cursor.execute(query)
rows = cursor.fetchall()

print(f"Found {len(rows)} matching rows")
for row in rows:
    print("\n--- ROW ---")
    d = dict(zip([c[1] for c in columns], row))
    for k, v in d.items():
        if k == 'content':
            print(f"{k} (repr): {repr(v)}")
        else:
            print(f"{k}: {v}")

conn.close()
