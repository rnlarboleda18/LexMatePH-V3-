import psycopg2

DB_URL = "postgresql://bar_admin:[DB_PASSWORD]@bar-db-eu-west.postgres.database.azure.com:5432/postgres?sslmode=require"

def main():
    print("Connecting to Cloud DB...")
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    print("Deleting misaligned Evidence headers (assigned to Rule 1)...")
    cur.execute("""
        DELETE FROM roc_codal 
        WHERE book_label = 'Evidence' 
          AND title_label = 'Rule 1'
    """)
    deleted = cur.rowcount
    print(f"  Deleted {deleted} broken rows.")

    print("\nInserting correct Evidence headers into Rule 132...")
    
    corrections = [
        {
            "article_title": "B. AUTHENTICATION AND PROOF OF DOCUMENTS",
            "title_label": "Rule 132",
            "section_num": 18,
            "article_num": "Rule 132, Section 18 - Header",
            "content_md": "## B. AUTHENTICATION AND PROOF OF DOCUMENTS"
        },
        {
            "article_title": "C. OFFER AND OBJECTION",
            "title_label": "Rule 132",
            "section_num": 33,
            "article_num": "Rule 132, Section 33 - Header",
            "content_md": "## C. OFFER AND OBJECTION"
        }
    ]

    for c in corrections:
        cur.execute("""
            INSERT INTO roc_codal (
                id, book, book_label, title_label, section_num, 
                article_num, article_title, content_md, created_at, updated_at
            ) VALUES (
                gen_random_uuid(), 4, 'Evidence', %s, %s,
                %s, %s, %s, NOW(), NOW()
            )
        """, (
            c['title_label'], c['section_num'], c['article_num'],
            c['article_title'], c['content_md']
        ))
        print(f"  Inserted: {c['article_title']!r} at {c['title_label']}, Section {c['section_num']}")

    conn.commit()
    print("\n🎉 Repair complete!")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
