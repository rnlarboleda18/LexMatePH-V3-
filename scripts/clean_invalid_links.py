import psycopg2
from psycopg2.extras import RealDictCursor
import os

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"

conn = psycopg2.connect(DB_CONNECTION_STRING)
cur = conn.cursor(cursor_factory=RealDictCursor)

print("\n=== CLEANING INVALID ARTICLE 2 LINKS ===\n")

# Find links where AI said "does not interpret"
cur.execute("""
    SELECT 
        l.id,
        l.case_id,
        s.short_title,
        l.specific_ruling
    FROM codal_case_links l
    JOIN sc_decided_cases s ON l.case_id = s.id
    WHERE l.statute_id = 'RPC' 
      AND l.provision_id = '2'
      AND (
          l.specific_ruling ILIKE '%does not interpret%'
          OR l.specific_ruling ILIKE '%not applicable%'
          OR l.specific_ruling ILIKE '%no direct relation%'
          OR (l.target_paragraph_index = -1 AND l.specific_ruling != 'General')
      )
""")

invalid_links = cur.fetchall()

if invalid_links:
    print(f"Found {len(invalid_links)} invalid links:")
    for link in invalid_links:
        print(f"  - {link['short_title']}")
        print(f"    → {link['specific_ruling'][:100]}...")
    
    response = input(f"\nDelete these {len(invalid_links)} invalid links? (yes/no): ")
    
    if response.lower() == 'yes':
        link_ids = [link['id'] for link in invalid_links]
        cur.execute("""
            DELETE FROM codal_case_links
            WHERE id = ANY(%s)
        """, (link_ids,))
        conn.commit()
        print(f"✓ Deleted {len(invalid_links)} invalid links!")
    else:
        print("Operation cancelled.")
else:
    print("No invalid links found.")

conn.close()
