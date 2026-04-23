"""Run against whatever DB the API actually uses (production cloud)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_CONNECTION_STRING

import psycopg2
from psycopg2.extras import RealDictCursor

print(f"Connecting to: {DB_CONNECTION_STRING.split('@')[-1].split('/')[0]}")
conn = psycopg2.connect(DB_CONNECTION_STRING, connect_timeout=15)
cur = conn.cursor(cursor_factory=RealDictCursor)

# 1. All statute_id counts
cur.execute(
    "SELECT statute_id::text AS sid, COUNT(*) c FROM codal_case_links GROUP BY statute_id ORDER BY c DESC LIMIT 20"
)
print("\nstatute_id counts in production DB:")
for r in cur.fetchall():
    print(f"  {r['sid']}: {r['c']}")

# 2. Exact RPC check
cur.execute("SELECT COUNT(*) c FROM codal_case_links WHERE UPPER(TRIM(statute_id::text)) = 'RPC'")
print(f"\nRPC rows (exact): {cur.fetchone()['c']}")

# 3. Check legal_codes for RPC UUID
cur.execute("SELECT code_id::text, short_name FROM legal_codes WHERE UPPER(TRIM(short_name)) = 'RPC' LIMIT 1")
lc = cur.fetchone()
print(f"\nlegal_codes RPC: {lc}")

if lc:
    cur.execute("SELECT COUNT(*) c FROM codal_case_links WHERE statute_id::text = %s", (lc['code_id'],))
    print(f"codal_case_links rows under RPC code_id UUID: {cur.fetchone()['c']}")

# 4. Sample RPC links whatever form
cur.execute(
    """
    SELECT statute_id::text, provision_id::text, target_paragraph_index, COUNT(*) n
    FROM codal_case_links
    WHERE statute_id::text ILIKE '%rpc%' OR statute_id::text ILIKE '%penal%'
       OR statute_id::text ILIKE '%3815%'
    GROUP BY statute_id, provision_id, target_paragraph_index
    ORDER BY n DESC LIMIT 5
    """
)
print("\nRPC-like rows:", cur.fetchall())

# 5. Check if there are rpc_codal articles with links stored under any statute
cur.execute("SELECT article_num FROM rpc_codal LIMIT 3")
sample_arts = [r['article_num'] for r in cur.fetchall()]
print(f"\nSample rpc_codal article_nums: {sample_arts}")
for a in sample_arts:
    cur.execute(
        "SELECT statute_id::text, COUNT(*) n FROM codal_case_links WHERE provision_id = %s GROUP BY statute_id",
        (str(a),)
    )
    rows = cur.fetchall()
    if rows:
        print(f"  Article {a} links: {[dict(r) for r in rows]}")
    else:
        print(f"  Article {a}: no links")

conn.close()
