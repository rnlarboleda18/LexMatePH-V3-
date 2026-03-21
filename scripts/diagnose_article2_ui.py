import psycopg2
from psycopg2.extras import RealDictCursor
import os
import json

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"

conn = psycopg2.connect(DB_CONNECTION_STRING)
cur = conn.cursor(cursor_factory=RealDictCursor)

print("\n=== COMPLETE ARTICLE 2 DIAGNOSIS ===\n")

# 1. Check what the API endpoint would return
print("1. API RESPONSE SIMULATION (what /api/rpc/book/1 returns):")
cur.execute("""
    SELECT article_num FROM rpc_codal WHERE article_num = '2'
""")
articles = cur.fetchall()

# Simulate attach_link_counts function
article_nums = ['2']
cur.execute("""
    SELECT provision_id, target_paragraph_index, COUNT(*) as link_count
    FROM codal_case_links 
    WHERE statute_id = 'RPC' 
      AND provision_id = ANY(%s)
      AND target_paragraph_index IS NOT NULL
      AND target_paragraph_index >= 0
    GROUP BY provision_id, target_paragraph_index
""", (article_nums,))
rows = cur.fetchall()

link_map = {}
for r in rows:
    art = r['provision_id']
    idx = r['target_paragraph_index']
    count = r['link_count']
    
    if art not in link_map:
        link_map[art] = {}
    link_map[art][idx] = count

print(f"  paragraph_links for Article 2: {link_map.get('2', {})}")

# 2. Check content structure
print("\n2. CONTENT STRUCTURE:")
cur.execute("SELECT content_md FROM rpc_codal WHERE article_num = '2'")
content_row = cur.fetchone()
content = content_row['content_md']

segments = content.split('\n\n')
print(f"  Total segments (split by \\n\\n): {len(segments)}")
for i, seg in enumerate(segments):
    preview = seg[:60].replace('\n', ' ').strip()
    count = link_map.get('2', {}).get(i, 0)
    status = f"🔨 {count}" if count > 0 else "  -"
    print(f"  [{i}] {status} {preview}...")

# 3. Show actual link details
print("\n3. ACTUAL LINKS:")
cur.execute("""
    SELECT 
        l.target_paragraph_index,
        s.short_title,
        l.specific_ruling
    FROM codal_case_links l
    JOIN sc_decided_cases s ON l.case_id = s.id
    WHERE l.statute_id = 'RPC' 
      AND l.provision_id = '2'
      AND l.target_paragraph_index >= 0
    ORDER BY l.target_paragraph_index
""")
links = cur.fetchall()

for link in links:
    print(f"  Para {link['target_paragraph_index']}: {link['short_title']}")
    print(f"    → {link['specific_ruling'][:80]}...")

conn.close()

print("\n=== EXPECTED BEHAVIOR ===")
print("If paragraph_links = {0: 1}, then:")
print("  - Segment 0 should show: 🔨 1")
print("  - All other segments should show: (no icon)")
