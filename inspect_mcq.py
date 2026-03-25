from db_pool import get_db_connection, put_db_connection
from psycopg2.extras import RealDictCursor
import re

def find_mcqs():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Let's pull questions containing potential MCQ headers that might be leaking
    cur.execute("""
        SELECT id, text 
        FROM questions 
        WHERE text ~* '\\(A\\)' 
           OR text ~* '^[A-D]\\.'
           OR text ~* '\\\\b[A-D]\\\\.'
        LIMIT 20
    """)
    rows = cur.fetchall()
    cur.close()
    put_db_connection(conn)
    
    print(f"Found {len(rows)} potential MCQs leaking/existing:")
    for r in rows:
        print(f"--- ID: {r['id']} ---")
        print(r['text'][:300] + "...")

if __name__ == '__main__':
    find_mcqs()
