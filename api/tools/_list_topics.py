import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(os.environ["DB_CONNECTION_STRING"])
cur = conn.cursor(cursor_factory=RealDictCursor)
cur.execute("SELECT COUNT(*) AS n FROM bar_reviewer_topics")
print("total rows:", cur.fetchone()["n"])
cur.execute("SELECT DISTINCT subject_id FROM bar_reviewer_topics")
print("subjects:", [r["subject_id"] for r in cur.fetchall()])
cur.execute("SELECT roman_num, sub_letter, status FROM bar_reviewer_topics LIMIT 5")
for r in cur.fetchall():
    print(repr(r["roman_num"]), repr(r["sub_letter"]), repr(r["status"]))
cur.close(); conn.close()
