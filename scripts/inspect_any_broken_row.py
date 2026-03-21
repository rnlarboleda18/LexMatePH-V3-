import psycopg2
from psycopg2.extras import RealDictCursor

DB_URL = "postgresql://bar_admin:RABpass021819!@bar-db-eu-west.postgres.database.azure.com:5432/postgres?sslmode=require"

def main():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    print("Querying for ANY broken ROC subheader in Cloud DB...")
    cur.execute("SELECT * FROM roc_codal")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    broken = []
    for r in rows:
        content = (r['content_md'] or "").strip()
        if content and content[0].islower():
            broken.append(r)

    if not broken:
        print("No broken rows found by that definition.")
        return

    first = broken[0]
    print(f"\n--- COLUMN DATA for ID {first['id']} ---")
    for k, v in first.items():
        print(f"{k}: {v!r}")

if __name__ == "__main__":
    main()
