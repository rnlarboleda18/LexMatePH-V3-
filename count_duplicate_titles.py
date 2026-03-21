import psycopg2
import json

settings_path = r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\api\local.settings.json'
with open(settings_path) as f:
    settings = json.load(f)

conn_str = settings['Values']['DB_CONNECTION_STRING']
conn = psycopg2.connect(conn_str)
cur = conn.cursor()

cur.execute("""
    SELECT COUNT(*), COUNT(DISTINCT article_num) 
    FROM const_codal 
    WHERE article_title ILIKE '%Declaration of Principles%'
""")
cnt, dist_cnt = cur.fetchone()

with open('output.txt', 'w') as out:
    out.write("Searching for duplicate 'Declaration of Principles' titles...\n")
    out.write(f"Total rows with title match: {cnt}\n")
    out.write(f"Distinct article_nums: {dist_cnt}\n")

    if cnt > 1:
        out.write("\nListing first 10 matches:\n")
        cur.execute("""
            SELECT id, article_num, article_title, group_header 
            FROM const_codal 
            WHERE article_title ILIKE '%Declaration of Principles%'
            LIMIT 10
        """)
        for r in cur.fetchall():
            out.write(f"ID: {r[0]} | Num: {r[1]} | Title: {r[2]} | Group: {r[3]}\n")

cur.close()
conn.close()
print("Done writing output.txt")
