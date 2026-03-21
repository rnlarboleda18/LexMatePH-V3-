import psycopg2
from psycopg2.extras import RealDictCursor
import os

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"

conn = psycopg2.connect(DB_CONNECTION_STRING)
cur = conn.cursor(cursor_factory=RealDictCursor)

print("=" * 80)
print("ARTICLE 8 LINKS")
print("=" * 80)
cur.execute("""
    SELECT 
        ccl.id,
        ccl.provision_id,
        ccl.target_paragraph_index,
        ccl.specific_ruling,
        sdc.short_title
    FROM codal_case_links ccl
    JOIN sc_decided_cases sdc ON ccl.case_id = sdc.id
    WHERE ccl.statute_id = 'RPC' AND ccl.provision_id = '8'
    ORDER BY ccl.target_paragraph_index
""")

for row in cur.fetchall():
    print(f"\nCase: {row['short_title']}")
    print(f"  Paragraph Index: {row['target_paragraph_index']}")
    print(f"  Summary: {row['specific_ruling'][:100]}...")

print("\n" + "=" * 80)
print("ARTICLE 217 LINKS")
print("=" * 80)
cur.execute("""
    SELECT 
        ccl.id,
        ccl.provision_id,
        ccl.target_paragraph_index,
        ccl.specific_ruling,
        sdc.short_title
    FROM codal_case_links ccl
    JOIN sc_decided_cases sdc ON ccl.case_id = sdc.id
    WHERE ccl.statute_id = 'RPC' AND ccl.provision_id = '217'
    ORDER BY ccl.target_paragraph_index
""")

for row in cur.fetchall():
    print(f"\nCase: {row['short_title']}")
    print(f"  Paragraph Index: {row['target_paragraph_index']}")
    print(f"  Summary: {row['specific_ruling'][:100]}...")

print("\n" + "=" * 80)
print("PARAGRAPH LINK COUNTS FOR ARTICLE 217")
print("=" * 80)
cur.execute("""
    SELECT target_paragraph_index, COUNT(*) as count
    FROM codal_case_links
    WHERE statute_id = 'RPC' AND provision_id = '217'
      AND target_paragraph_index IS NOT NULL
      AND target_paragraph_index >= 0
    GROUP BY target_paragraph_index
    ORDER BY target_paragraph_index
""")

for row in cur.fetchall():
    print(f"Paragraph {row['target_paragraph_index']}: {row['count']} cases")

print("\n" + "=" * 80)
print("GENERAL LINKS (paragraph_index = -1) FOR ARTICLE 217")
print("=" * 80)
cur.execute("""
    SELECT COUNT(*) as count
    FROM codal_case_links
    WHERE statute_id = 'RPC' AND provision_id = '217'
      AND target_paragraph_index = -1
""")
general_count = cur.fetchone()['count']
print(f"General article links: {general_count}")

conn.close()
