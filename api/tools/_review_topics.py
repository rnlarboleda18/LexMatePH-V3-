"""Quick DB query: print doctrine/distinctions for review topics."""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(os.environ["DB_CONNECTION_STRING"])
cur = conn.cursor(cursor_factory=RealDictCursor)
cur.execute("""
  SELECT roman_num, sub_letter, sub_heading, status,
         doctrine_md, distinctions_md, key_cases
  FROM bar_reviewer_topics
  WHERE subject_id = 'remedial'
    AND ((roman_num='VII' AND sub_letter='D')
      OR (roman_num='VIII' AND sub_letter IN ('A','D','E')))
  ORDER BY sort_order
""")
rows = cur.fetchall()
cur.close()
conn.close()

for r in rows:
    kc = r["key_cases"]
    if isinstance(kc, str):
        try:
            kc = json.loads(kc)
        except Exception:
            kc = []
    print(f"\n{'='*70}")
    print(f"TOPIC {r['roman_num']}.{r['sub_letter']} | {r['sub_heading']}")
    print(f"Status: {r['status']}  |  Cases: {len(kc) if isinstance(kc, list) else '?'}")
    print(f"\n--- DOCTRINE ---")
    print(r["doctrine_md"][:3000] if r["doctrine_md"] else "[NO DOCTRINE]")
    print(f"\n--- DISTINCTIONS ---")
    print(r["distinctions_md"][:1000] if r["distinctions_md"] else "[NONE]")

print(f"\nTotal rows found: {len(rows)}")
