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


with open('universe_gap_report_clean.txt', 'w') as f:
    f.write("UNIVERSE GAP ANALYSIS\n")
    f.write("="*30 + "\n\n")

    # 1. DIVISION CASES (1987-2025)
    f.write("[1] Division Cases (1987-2025)\n")
    cur.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE digest_facts IS NULL) as undigested,
            COUNT(*) FILTER (WHERE ai_model LIKE '%gemini-3%') as upgraded_v3,
            COUNT(*) FILTER (WHERE ai_model NOT LIKE '%gemini-3%' OR ai_model IS NULL) as needs_upgrade
        FROM sc_decided_cases 
        WHERE division != 'En Banc'
          AND date >= '1987-01-01'
          AND date <= '2025-12-31'
    """)
    res = cur.fetchone()
    f.write(f"   - Total: {res[0]:,}\n")
    f.write(f"   - Undigested (Critical): {res[1]:,}\n")
    f.write(f"   - Upgraded to V3: {res[2]:,}\n")
    f.write(f"   - Needs Upgrade: {res[3]:,}\n\n")

    # 2. EN BANC PENDING (1987-2025)
    f.write("[2] En Banc Cases (1987-2025) - Outside Active Fleets\n")
    
    cur.execute("""
        SELECT 
            'Phase 2 (100K-1M)' as category,
            COUNT(*) 
        FROM sc_decided_cases 
        WHERE division = 'En Banc' 
          AND date >= '1987-01-01'
          AND LENGTH(full_text_md) BETWEEN 100000 AND 1000000
          AND (ai_model NOT LIKE '%gemini-3%' OR ai_model IS NULL)
    """)
    p2 = cur.fetchone()
    f.write(f"   - {p2[0]}: {p2[1]:,} (Planned for Phase 2)\n")

    cur.execute("""
        SELECT 
            'Phase 3 (>1M chars)' as category,
            COUNT(*) 
        FROM sc_decided_cases 
        WHERE division = 'En Banc' 
          AND date >= '1987-01-01'
          AND LENGTH(full_text_md) > 1000000
    """)
    p3 = cur.fetchone()
    f.write(f"   - {p3[0]}: {p3[1]:,} (Ultra-Large Cases)\n\n")

    # 3. GHOST CASES (Any Era)
    f.write("[3] 'Ghost' Cases (Any Era)\n")
    f.write("   (Cases with Full Text but NO Digest Facts)\n")
    cur.execute("""
        SELECT 
            CASE 
                WHEN date < '1987-01-01' THEN 'Historical (1901-1986)'
                WHEN division = 'En Banc' THEN 'Modern En Banc'
                ELSE 'Modern Division'
            END as category,
            COUNT(*) 
        FROM sc_decided_cases 
        WHERE full_text_md IS NOT NULL 
          AND digest_facts IS NULL
        GROUP BY 1
        ORDER BY 1
    """)
    rows = cur.fetchall()
    for cat, count in rows:
        f.write(f"   - {cat}: {count:,}\n")
    if not rows:
        f.write("   - None! All text-bearing cases have digests.\n")

print("Report written to universe_gap_report_clean.txt")
conn.close()
