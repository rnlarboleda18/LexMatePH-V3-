import psycopg2

conn_str = "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"
conn = psycopg2.connect(conn_str)
cur = conn.cursor()

# Delete all Article 329 versions
cur.execute("""
    DELETE FROM article_versions
    WHERE code_id = '570b007a-36b6-4e74-a993-4b8d5d17a4ef'
        AND article_number = '329'
""")

conn.commit()
print(f"Deleted {cur.rowcount} versions of Article 329")

# Re-ingest the original version from RPC.md
import os
import re

md_file = 'data/Codals/md/RPC.md'

with open(md_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find Article 329
current_article = None
current_content = []

header_pattern = re.compile(r'^###\s+(Article\s+(\d+)\..+)')

for line in lines:
    match = header_pattern.match(line)
    if match:
        # Save previous article if it's 329
        if current_article and current_article[1] == '329':
            article_label = current_article[0]
            content = f"### {article_label}\n\n{''.join(current_content).strip()}"
            
            # Insert into database
            cur.execute("""
                INSERT INTO article_versions
                (code_id, article_number, content, valid_from, valid_to, amendment_id)
                VALUES (%s, %s, %s, %s, NULL, %s)
            """, ('570b007a-36b6-4e74-a993-4b8d5d17a4ef', '329', content, '1932-01-01', 'Act No. 3815'))
            
            conn.commit()
            print(f"Re-ingested original Article 329")
            break
        
        # Start new article
        current_article = (match.group(1), match.group(2))
        current_content = []
    else:
        if current_article:
            current_content.append(line)

conn.close()
print("Ready to re-apply amendment!")
