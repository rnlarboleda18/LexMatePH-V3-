import psycopg2

conn_str = "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"
conn = psycopg2.connect(conn_str)
cur = conn.cursor()

print("Article 329 Versions - Temporal History:")
print("=" * 100)

cur.execute("""
    SELECT 
        article_number,
        LEFT(content, 80) as content_preview,
        valid_from,
        valid_to,
        amendment_id
    FROM article_versions
    WHERE code_id = '570b007a-36b6-4e74-a993-4b8d5d17a4ef'
        AND article_number = '329'
    ORDER BY valid_from
""")

for row in cur.fetchall():
    article_num, content, valid_from, valid_to, amendment_id = row
    status = "CURRENT" if valid_to is None else "HISTORICAL"
    print(f"\n[{status}] Article {article_num}")
    print(f"  Valid From: {valid_from}")
    print(f"  Valid To:   {valid_to or 'NULL (still active)'}")
    print(f"  Amendment:  {amendment_id}")
    print(f"  Content:    {content}...")

conn.close()
print("\n" + "=" * 100)
