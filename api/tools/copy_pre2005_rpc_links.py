"""
Copy missing 1964-2004 RPC links from local DB to Azure production.
1922-1963 were already copied. This script fills in the gap.
"""
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
import uuid
import sys

LOCAL_DSN = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"
PROD_DSN  = "postgres://bar_admin:RABpass021819!@lexmateph-ea-db.postgres.database.azure.com:5432/lexmateph-ea-db?sslmode=require"

BATCH = 500

def main():
    local = psycopg2.connect(LOCAL_DSN)
    prod  = psycopg2.connect(PROD_DSN)
    lc = local.cursor(cursor_factory=RealDictCursor)
    pc = prod.cursor()

    # 1. Get valid case_ids in production for 1964-2004
    print("Fetching valid 1964-2004 case_ids from production sc_decided_cases...")
    sys.stdout.flush()
    pc.execute("""
        SELECT id FROM sc_decided_cases
        WHERE date IS NOT NULL
          AND date >= '1964-01-01'
          AND date < '2005-01-01'
    """)
    prod_valid_ids = {r[0] for r in pc.fetchall()}
    print(f"  Production has {len(prod_valid_ids)} cases in 1964-2004")
    sys.stdout.flush()

    # 2. Fetch local 1964-2004 RPC links
    print("Fetching 1964-2004 RPC links from local DB...")
    sys.stdout.flush()
    lc.execute("""
        SELECT ccl.*
        FROM codal_case_links ccl
        JOIN sc_decided_cases s ON s.id = ccl.case_id
        WHERE ccl.statute_id = 'RPC'
          AND s.date IS NOT NULL
          AND s.date >= '1964-01-01'
          AND s.date < '2005-01-01'
        ORDER BY s.date ASC
    """)
    local_rows = lc.fetchall()
    print(f"  Local has {len(local_rows)} links in 1964-2004")
    sys.stdout.flush()

    # 3. Filter to only valid case_ids
    valid_rows = [r for r in local_rows if r['case_id'] in prod_valid_ids]
    skipped = len(local_rows) - len(valid_rows)
    print(f"  After filtering: {len(valid_rows)} to insert, {skipped} skipped")
    sys.stdout.flush()

    if not valid_rows:
        print("Nothing to insert.")
        return

    cols = [k for k in valid_rows[0].keys() if k != 'id']
    col_str = 'id, ' + ', '.join(cols)

    # 4. Bulk-insert in batches
    inserted = 0
    for i in range(0, len(valid_rows), BATCH):
        batch = valid_rows[i:i+BATCH]
        values = [[str(uuid.uuid4())] + [r[c] for c in cols] for r in batch]
        execute_values(pc, f"INSERT INTO codal_case_links ({col_str}) VALUES %s", values)
        prod.commit()
        inserted += len(batch)
        print(f"  Inserted {inserted}/{len(valid_rows)}...")
        sys.stdout.flush()

    print(f"\nDone. Inserted {inserted} rows total.")

    # 5. Final verification
    pc.execute("""
        SELECT EXTRACT(YEAR FROM s.date)::int AS yr, COUNT(*) cnt
        FROM codal_case_links ccl
        JOIN sc_decided_cases s ON s.id = ccl.case_id
        WHERE ccl.statute_id = 'RPC'
        GROUP BY yr ORDER BY yr ASC
    """)
    print("\nFull production year distribution:")
    for r in pc.fetchall():
        print(f"  {r[0]}: {r[1]}")

    pc.execute("SELECT COUNT(*) FROM codal_case_links WHERE statute_id='RPC'")
    print(f"\nTotal production RPC links: {pc.fetchone()[0]}")

    lc.close(); pc.close()
    local.close(); prod.close()

if __name__ == '__main__':
    main()
