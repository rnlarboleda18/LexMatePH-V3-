import psycopg2
import json

try:
    with open('api/local.settings.json') as f:
        settings = json.load(f)
        DB_CONNECTION_STRING = settings['Values']['DB_CONNECTION_STRING']
except:
    DB_CONNECTION_STRING = "postgresql://postgres:password@localhost:5432/sc_decisions"

conn = psycopg2.connect(DB_CONNECTION_STRING)
cur = conn.cursor()

# Question 1: When were these digests created?
print("\n" + "="*70)
print("INVESTIGATION: Why Re-Digest gemini-2.5-flash-lite Cases?")
print("="*70 + "\n")

# Check creation dates
cur.execute("""
    SELECT 
        DATE(created_at) as creation_date,
        COUNT(*) as count
    FROM sc_decided_cases
    WHERE division = 'En Banc'
      AND ai_model = 'gemini-2.5-flash-lite'
      AND created_at IS NOT NULL
    GROUP BY DATE(created_at)
    ORDER BY creation_date DESC
    LIMIT 10
""")

print("Recent Creation Dates (gemini-2.5-flash-lite):")
print(f"{'Date':<12} | {'Cases':>6}")
print("-" * 20)
for row in cur.fetchall():
    print(f"{str(row[0]):<12} | {row[1]:>6,}")

# Question 2: Sample a recent case to check its quality
cur.execute("""
    SELECT 
        id,
        short_title,
        CASE WHEN separate_opinions IS NOT NULL AND separate_opinions::text != '[]' THEN 'YES' ELSE 'NO' END,
        CASE WHEN digest_facts LIKE '%Antecedents%' THEN 'YES' ELSE 'NO' END,
        created_at
    FROM sc_decided_cases
    WHERE division = 'En Banc'
      AND ai_model = 'gemini-2.5-flash-lite'
      AND date >= '2020-01-01'
    ORDER BY created_at DESC
    LIMIT 3
""")

print(f"\n{'='*70}")
print("Sample Recent Cases (Quality Check):")
print(f"{'='*70}")
for row in cur.fetchall():
    print(f"\nCase ID: {row[0]} - {row[1]}")
    print(f"  Created: {str(row[4])[:19]}")
    print(f"  Has Separate Opinions: {row[2]}")
    print(f"  Has Structured Facts: {row[3]}")

# Question 3: Were separate opinions REQUESTED in the original prompt?
# (We can't know directly, but we can infer from the pattern)
cur.execute("""
    SELECT 
        COUNT(*) FILTER (WHERE separate_opinions IS NULL OR separate_opinions::text = '[]') as missing,
        COUNT(*) as total,
        ROUND(COUNT(*) FILTER (WHERE separate_opinions IS NULL OR separate_opinions::text = '[]')::numeric / COUNT(*) * 100, 1) as pct_missing
    FROM sc_decided_cases
    WHERE division = 'En Banc'
      AND ai_model = 'gemini-2.5-flash-lite'
      AND date >= '2020-01-01'
""")

row = cur.fetchone()
print(f"\n{'='*70}")
print(f"Separate Opinions Analysis (2020+ cases):")
print(f"{'='*70}")
print(f"Missing: {row[0]:,}/{row[1]:,} ({row[2]}%)")

if row[2] > 80:
    print("\n⚠️  CONCLUSION: Likely original prompt DID NOT request separate opinions")
else:
    print("\n❓ CONCLUSION: Original prompt requested them but model failed to deliver")

conn.close()
