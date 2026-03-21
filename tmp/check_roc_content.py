import psycopg2
from psycopg2.extras import RealDictCursor
import os

conn = psycopg2.connect('postgresql://bar_admin:RABpass021819!@bar-db-eu-west.postgres.database.azure.com:5432/postgres?sslmode=require')
cur = conn.cursor(cursor_factory=RealDictCursor)

sections_to_check = [
    (132, 19), # Rule 132, Section 19 (Flush left in UI)
    (18, 2),   # Rule 18, Section 2 (Indented/Tight in UI)
    (18, 7),   # Rule 18, Section 7 (Flush left? Check screenshot 2)
    (13, 3)    # Rule 13, Section 3 (Tight check)
]

output = ""
for rule, sec in sections_to_check:
    cur.execute("SELECT section_content FROM roc_codal WHERE rule_num = %s AND section_num = %s", (rule, sec))
    row = cur.fetchone()
    if row:
        output += f"--- RULE {rule} SECTION {sec} ---\n"
        output += repr(row['section_content']) + "\n\n"
    else:
        output += f"--- RULE {rule} SECTION {sec} NOT FOUND ---\n\n"

out_path = r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\tmp\check_roc.txt'
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(output)

print(f"Wrote output to {out_path}")

cur.close()
conn.close()
