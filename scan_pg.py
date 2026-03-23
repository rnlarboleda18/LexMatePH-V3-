import psycopg2
import json

conn_str = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"

try:
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor()
    
    query = "SELECT id, question_id, text FROM answers WHERE text LIKE '%Q:%'"
    cur.execute(query)
    mixed = cur.fetchall()
    
    with open('mixed_answers_report.md', 'w', encoding='utf-8') as f:
        f.write("# Mixed Questions in Answers Report\n\n")
        f.write(f"Found {len(mixed)} answers containing 'Q:'\n\n")
        
        for m in mixed:
            ans_id = m[0]
            q_id = m[1]
            text = m[2]
            f.write(f"## Answer ID: {ans_id} (Associated Question ID: {q_id})\n")
            f.write("```text\n")
            f.write(text)
            f.write("\n```\n\n")
            
    print("Report written to mixed_answers_report.md")
    
except Exception as e:
    print("Error:", e)
