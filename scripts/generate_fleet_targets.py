import psycopg2
import json

with open('local.settings.json') as f:
    conn_str = json.load(f)['Values']['DB_CONNECTION_STRING']

conn = psycopg2.connect(conn_str)
cur = conn.cursor()

print("Generating Fleet Target Lists...")

# Fleet 1: <50K chars, never digested
cur.execute("""
    SELECT id 
    FROM sc_decided_cases
    WHERE ai_model IS NULL 
      AND full_text_md IS NOT NULL
      AND LENGTH(full_text_md) > 0
      AND LENGTH(full_text_md) < 50000
    ORDER BY id
""")
fleet1_ids = [r[0] for r in cur.fetchall()]
with open('fleet1_smallcases_ids.txt', 'w') as f:
    f.write('\n'.join(map(str, fleet1_ids)))
print(f"Fleet 1 (Small <50K): {len(fleet1_ids)} cases")

# Fleet 2: 50-100K chars, never digested
cur.execute("""
    SELECT id 
    FROM sc_decided_cases
    WHERE ai_model IS NULL 
      AND full_text_md IS NOT NULL
      AND LENGTH(full_text_md) BETWEEN 50000 AND 99999
    ORDER BY id
""")
fleet2_ids = [r[0] for r in cur.fetchall()]
with open('fleet2_mediumcases_ids.txt', 'w') as f:
    f.write('\n'.join(map(str, fleet2_ids)))
print(f"Fleet 2 (Medium 50-100K): {len(fleet2_ids)} cases")

# Fleet 3: Significance backfill only
cur.execute("""
    SELECT id 
    FROM sc_decided_cases
    WHERE ai_model IS NOT NULL
      AND significance_category IS NULL
    ORDER BY id
""")
fleet3_ids = [r[0] for r in cur.fetchall()]
with open('fleet3_significance_ids.txt', 'w') as f:
    f.write('\n'.join(map(str, fleet3_ids)))
print(f"Fleet 3 (Significance): {len(fleet3_ids)} cases")

# Fleet 4: Missing main_doctrine
cur.execute("""
    SELECT id 
    FROM sc_decided_cases
    WHERE ai_model IS NOT NULL
      AND (main_doctrine IS NULL OR main_doctrine = '')
    ORDER BY id
""")
fleet4_ids = [r[0] for r in cur.fetchall()]
with open('fleet4_doctrine_ids.txt', 'w') as f:
    f.write('\n'.join(map(str, fleet4_ids)))
print(f"Fleet 4 (Doctrine): {len(fleet4_ids)} cases")

# Fleet 5: Missing facts or ruling
cur.execute("""
    SELECT DISTINCT id 
    FROM sc_decided_cases
    WHERE ai_model IS NOT NULL
      AND (
          (digest_facts IS NULL OR digest_facts = '') OR
          (digest_ruling IS NULL OR digest_ruling = '')
      )
    ORDER BY id
""")
fleet5_ids = [r[0] for r in cur.fetchall()]
with open('fleet5_factsruling_ids.txt', 'w') as f:
    f.write('\n'.join(map(str, fleet5_ids)))
print(f"Fleet 5 (Facts/Ruling): {len(fleet5_ids)} cases")

print(f"\nTotal targets: {len(fleet1_ids) + len(fleet2_ids) + len(fleet3_ids) + len(fleet4_ids) + len(fleet5_ids)}")

conn.close()
