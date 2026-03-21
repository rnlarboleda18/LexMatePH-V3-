import psycopg2
import json
from datetime import datetime

with open('local.settings.json') as f:
    conn_str = json.load(f)['Values']['DB_CONNECTION_STRING']

conn = psycopg2.connect(conn_str)
cur = conn.cursor()

print("=" * 80)
print("COMPREHENSIVE DIGEST AUDIT")
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)

# 1. NEVER DIGESTED - by character size (Ghost tiers)
print("\n### 1. NEVER DIGESTED CASES (No AI Model) ###")
print("Divided by full_text_md character count:\n")

cur.execute("""
    SELECT 
        CASE 
            WHEN LENGTH(full_text_md) < 50000 THEN '<50K'
            WHEN LENGTH(full_text_md) BETWEEN 50000 AND 99999 THEN '50-100K'
            ELSE '>100K'
        END AS size_tier,
        COUNT(*) as count
    FROM sc_decided_cases
    WHERE ai_model IS NULL 
      AND full_text_md IS NOT NULL
      AND LENGTH(full_text_md) > 0
    GROUP BY size_tier
    ORDER BY size_tier
""")

never_digested = cur.fetchall()
total_never = sum(r[1] for r in never_digested)

for tier, count in never_digested:
    print(f"  {tier:>10} chars: {count:>5} cases")
print(f"  {'TOTAL':>10}:       {total_never:>5} cases")

# 2. SIGNIFICANCE BACKFILL ONLY
print("\n### 2. SIGNIFICANCE BACKFILL ONLY ###")
print("(Has AI digest but missing significance_category)\n")

cur.execute("""
    SELECT COUNT(*)
    FROM sc_decided_cases
    WHERE ai_model IS NOT NULL
      AND significance_category IS NULL
""")

sig_backfill = cur.fetchone()[0]
print(f"  Cases needing significance: {sig_backfill}")

# 3. OTHER BACKFILLS (excluding significance)
print("\n### 3. OTHER FIELD BACKFILLS ###")
print("(Has AI model but missing key fields other than significance)\n")

# Main doctrine missing
cur.execute("""
    SELECT COUNT(*)
    FROM sc_decided_cases
    WHERE ai_model IS NOT NULL
      AND (main_doctrine IS NULL OR main_doctrine = '')
""")
main_doctrine_missing = cur.fetchone()[0]

# Facts missing
cur.execute("""
    SELECT COUNT(*)
    FROM sc_decided_cases
    WHERE ai_model IS NOT NULL
      AND (digest_facts IS NULL OR digest_facts = '')
""")
facts_missing = cur.fetchone()[0]

# Ruling missing
cur.execute("""
    SELECT COUNT(*)
    FROM sc_decided_cases
    WHERE ai_model IS NOT NULL
      AND (digest_ruling IS NULL OR digest_ruling = '')
""")
ruling_missing = cur.fetchone()[0]

# At least one field missing (but not significance)
cur.execute("""
    SELECT COUNT(*)
    FROM sc_decided_cases
    WHERE ai_model IS NOT NULL
      AND (
          (main_doctrine IS NULL OR main_doctrine = '') OR
          (digest_facts IS NULL OR digest_facts = '') OR
          (digest_ruling IS NULL OR digest_ruling = '')
      )
""")
other_backfill = cur.fetchone()[0]

print(f"  Missing main_doctrine: {main_doctrine_missing}")
print(f"  Missing digest_facts:  {facts_missing}")
print(f"  Missing digest_ruling: {ruling_missing}")
print(f"  ---")
print(f"  Total needing backfill: {other_backfill}")


# SUMMARY
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Never Digested (Total):      {total_never:>6} cases")
print(f"Significance Backfill Only:  {sig_backfill:>6} cases")
print(f"Other Field Backfills:       {other_backfill:>6} cases")
print(f"---")
print(f"TOTAL WORK REMAINING:        {total_never + sig_backfill + other_backfill:>6} cases")
print("=" * 80)

# Write summary to JSON for easy parsing
summary = {
    "timestamp": datetime.now().isoformat(),
    "never_digested": {
        "by_size": {tier: count for tier, count in never_digested},
        "total": total_never
    },
    "significance_backfill": sig_backfill,
    "other_backfill": {
        "main_doctrine_missing": main_doctrine_missing,
        "facts_missing": facts_missing,
        "ruling_missing": ruling_missing,
        "total": other_backfill
    },
    "total_work": total_never + sig_backfill + other_backfill
}

with open('audit_summary.json', 'w') as f:
    json.dump(summary, f, indent=2)

print("\nSummary saved to: audit_summary.json")

conn.close()

