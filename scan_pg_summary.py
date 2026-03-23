import psycopg2
import json

conn_str = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"

try:
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor()
    
    query = "SELECT id, question_id, substring(text from 1 for 100) FROM answers WHERE text LIKE '%Q:%'"
    cur.execute(query)
    mixed = cur.fetchall()
    
    out_path = r'C:\Users\rnlar\.gemini\antigravity\brain\8ce3b128-f35e-424f-b646-783b7d1e9870\mixed_answers_summary.md'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write("# Compact Report of Mixed Answers\n\n")
        f.write(f"Found {len(mixed)} answers containing 'Q:'.\n")
        f.write("Here is the list of Answer IDs with their associated Question IDs and a short preview:\n\n")
        
        f.write("| Answer ID | Question ID | Preview |\n")
        f.write("| --- | --- | --- |\n")
        for m in mixed:
            ans_id = m[0]
            q_id = m[1]
            text = m[2].replace('\n', ' ')
            f.write(f"| {ans_id} | {q_id} | {text} |\n")
            
    print("Report summary written.")
    
except Exception as e:
    print("Error:", e)
