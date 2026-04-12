import json
import os
import sys

# Load Azure Functions local.settings.json for standalone script execution
try:
    with open('local.settings.json', 'r') as f:
        settings = json.load(f)
        for k, v in settings.get('Values', {}).items():
            os.environ[k] = v
except FileNotFoundError:
    pass

from db_pool import get_db_connection, put_db_connection
from psycopg2.extras import RealDictCursor
import re

def find_mcqs():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute(r"""
        SELECT q.id, q.text, a.text as answer
        FROM questions q
        LEFT JOIN answers a ON a.question_id = q.id
        WHERE q.text ~* '\([a-d]\)' OR q.text ~* '\b[a-d]\.'
        LIMIT 10
    """)
    rows = cur.fetchall()
    cur.close()
    put_db_connection(conn)
    
    print(f"Found {len(rows)} potential MCQs leaking/existing:")
    for r in rows:
        print(f"--- ID: {r['id']} ---")
        print(r['text'][:200] + "...")

if __name__ == '__main__':
    find_mcqs()
