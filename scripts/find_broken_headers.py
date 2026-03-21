import psycopg2
from psycopg2.extras import RealDictCursor

DB_URL = "postgresql://bar_admin:RABpass021819!@bar-db-eu-west.postgres.database.azure.com:5432/postgres?sslmode=require"

def main():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    print("Searching for broken ROC subheaders in Cloud DB...")
    # Find rows where content_md starts with lowercase letter or matches split fragments
    # We load all rows and check in Python for accurate regex or lowercase starts
    cur.execute("SELECT id, article_num, section_label, content_md FROM roc_codal")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    broken = []
    for r in rows:
        content = (r['content_md'] or "").strip()
        label = (r['section_label'] or "").strip()
        
        if not content:
            continue
            
        # Standard indicators of a cut-off header:
        # 1. content starts with lowercase
        if content[0].islower():
            broken.append(r)
        # 2. Section label ends in known cutoff word-stubs (Non, co, an, with, etc.)
        elif label.endswith("Non") or label.endswith("co") or label.endswith("and"):
            broken.append(r)

    print(f"\nFound {len(broken)} potentially broken subheaders:\n")
    for b in broken[:15]:
        snippet_content = (b['content_md'] or "")[:60].replace("\n", " ")
        print(f"ID: {b['id']} | Label: {b['section_label']!r}")
        print(f"    Content: {snippet_content!r}\n")
        
    if len(broken) > 15:
        print(f"... and {len(broken) - 15} more.")

if __name__ == "__main__":
    main()
