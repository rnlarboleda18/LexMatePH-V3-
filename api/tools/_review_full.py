"""Print FULL doctrine for specific topics for manual review."""
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
cur.close(); conn.close()

for r in rows:
    kc = r["key_cases"]
    if isinstance(kc, str):
        try: kc = json.loads(kc)
        except: kc = []
    print(f"\n{'='*70}")
    print(f"TOPIC {r['roman_num']}.{r['sub_letter']} | {r['sub_heading']}")
    print(f"Status: {r['status']}  |  Cases: {len(kc) if isinstance(kc,list) else '?'}")
    if isinstance(kc, list):
        for c in kc:
            if isinstance(c, dict):
                print(f"  CASE: {c.get('short_title','')} | {c.get('case_number','')} | {c.get('date','')}")
            else:
                print(f"  CASE: {c}")
    print(f"\n--- FULL DOCTRINE ---")
    print(r["doctrine_md"] or "[NO DOCTRINE]")
    print(f"\n--- FULL DISTINCTIONS ---")
    print(r["distinctions_md"] or "[NONE]")

print("\nDone.")
