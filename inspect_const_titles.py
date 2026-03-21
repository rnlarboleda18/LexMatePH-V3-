import psycopg2
import json
import os

# Connect to DB
settings_path = r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\api\local.settings.json'
with open(settings_path) as f:
    settings = json.load(f)

conn_str = settings['Values']['DB_CONNECTION_STRING']
conn = psycopg2.connect(conn_str)
cur = conn.cursor()

print("Dumping const_codal titles to check for duplicates...")

cur.execute("""
    SELECT article_num, article_title, group_header 
    FROM const_codal 
    ORDER BY id ASC
""")

rows = cur.fetchall()
for i, row in enumerate(rows):
    if i > 50:  # Cap for speed, or remove cap to see all
        break
    print(f"Num: {row[0]} | Title: {row[1]} | Group: {row[2]}")

cur.close()
conn.close()
print("Done.")
