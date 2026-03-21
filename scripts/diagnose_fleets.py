import psycopg2
import json

try:
    with open('api/local.settings.json') as f:
        settings = json.load(f)
        DB_CONNECTION_STRING = settings['Values']['DB_CONNECTION_STRING']
except:
    DB_CONNECTION_STRING = "postgresql://postgres:password@localhost:5432/sc_decisions"

conn = psycopg2.connect(DB_CONNECTION_STRING)
conn.set_session(isolation_level=psycopg2.extensions.ISOLATION_LEVEL_READ_UNCOMMITTED)
cur = conn.cursor()

print("DIAGNOSE FLEETS\n" + "="*50)

# 1. CHECK GHOST CASES
print("\n[GHOST FLEET DIAGNOSIS]")
# Check if ANY of the "Ghost" candidates (NULL digest + Full text + NULL division) have been updated recently
cur.execute("""
    SELECT 
        id, digest_facts, ai_model, division, updated_at
    FROM sc_decided_cases 
    WHERE full_text_md IS NOT NULL 
      AND (division IS NULL) -- The definition of our ghosts
    ORDER BY updated_at DESC
    LIMIT 5
""")
print("Top 5 Most Recently Updated 'Ghost' (Null Division) Cases:")
rows = cur.fetchall()
for r in rows:
    print(f"ID: {r[0]}, DigestLen: {len(r[1]) if r[1] else 0}, Model: {r[2]}, Div: {r[3]}, Updated: {r[4]}")

if not rows:
    print("No Ghost cases found (or none updated).")

# 2. CHECK TURBO FLEET
print("\n[TURBO FLEET DIAGNOSIS]")
# Check recent En Banc updates
cur.execute("""
    SELECT 
        ai_model, COUNT(*)
    FROM sc_decided_cases 
    WHERE division = 'En Banc' 
      AND date >= '1987-01-01'
    GROUP BY 1
""")
print("Model Distribution for En Banc (1987-2025):")
for r in cur.fetchall():
    print(f"Model: {r[0]} | Count: {r[1]}")

# 3. CHECK BACKFILL FLEET
print("\n[BACKFILL FLEET DIAGNOSIS]")
cur.execute("""
    SELECT 
        ai_model, COUNT(*)
    FROM sc_decided_cases 
    WHERE date < '1987-01-01'
    GROUP BY 1
""")
print("Model Distribution for Historical (<1987):")
for r in cur.fetchall():
    print(f"Model: {r[0]} | Count: {r[1]}")

conn.close()
