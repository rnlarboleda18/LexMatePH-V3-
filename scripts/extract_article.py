import psycopg2

conn_str = "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"
conn = psycopg2.connect(conn_str)
cur = conn.cursor()

# Get both versions
cur.execute("""
    SELECT valid_from, content
    FROM article_versions
    WHERE code_id = '570b007a-36b6-4e74-a993-4b8d5d17a4ef'
        AND article_number = '329'
    ORDER BY valid_from
""")

versions = cur.fetchall()

# Write to file
with open('article_329_full.txt', 'w', encoding='utf-8') as f:
    for i, (valid_from, content) in enumerate(versions, 1):
        f.write(f"\n{'='*80}\n")
        f.write(f"VERSION {i} (valid from {valid_from})\n")
        f.write(f"{'='*80}\n\n")
        f.write(content)
        f.write("\n\n")

conn.close()
print("Saved to article_329_full.txt")
