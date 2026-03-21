import psycopg2
from api.db_pool import get_db_connection
from psycopg2.extras import RealDictCursor

conn = get_db_connection()
cur = conn.cursor(cursor_factory=RealDictCursor)

cur.execute("SELECT id, article_num, section_label FROM consti_codal LIMIT 5 OFFSET 12")
for r in cur.fetchall():
    print(r)

print("\nFinding Article III, section 1:")
cur.execute("SELECT id, article_num, section_label FROM consti_codal WHERE article_num LIKE '%III-1%' LIMIT 2")
for r in cur.fetchall():
    print(r)
