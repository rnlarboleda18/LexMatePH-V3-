import psycopg2
from psycopg2.extras import RealDictCursor

DB_URL = "postgresql://bar_admin:RABpass021819!@bar-db-eu-west.postgres.database.azure.com:5432/postgres?sslmode=require"

def main():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    print("Fetching all ROC titles from Cloud DB...")
    cur.execute("SELECT DISTINCT article_title FROM roc_codal")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    titles_with_spaces = []
    for r in rows:
        title = (r['article_title'] or "").strip()
        if " " in title:
             titles_with_spaces.append(title)

    print(f"\nFound {len(titles_with_spaces)} titles with spaces. Listing unique values:\n")
    # Sort for easier reading
    titles_with_spaces.sort()
    for t in titles_with_spaces:
         print(f" - {t!r}")

if __name__ == "__main__":
    main()
