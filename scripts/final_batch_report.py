import psycopg2
import json

def get_db_connection():
    try:
        with open('local.settings.json') as f:
            settings = json.load(f)
            conn_str = settings['Values']['DB_CONNECTION_STRING']
    except Exception:
        conn_str = "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"
    return psycopg2.connect(conn_str)

def report_status():
    # Load original targets
    try:
        with open('target_redigest_ids.txt', 'r') as f:
            content = f.read().replace('\n', ',')
            target_ids = [int(x.strip()) for x in content.split(',') if x.strip().isdigit()]
    except FileNotFoundError:
        print("Error: target_redigest_ids.txt not found. Cannot calculate specific batch progress.")
        return

    total_target = len(target_ids)
    print(f"Total Target Batch: {total_target}")

    conn = get_db_connection()
    cur = conn.cursor()

    # Count how many have been updated (i.e., NO LONGER 'gemini-2.5-flash-lite')
    cur.execute("""
        SELECT COUNT(*) 
        FROM sc_decided_cases 
        WHERE id = ANY(%s) 
          AND ai_model != 'gemini-2.5-flash-lite'
    """, (target_ids,))
    
    done = cur.fetchone()[0]
    remaining = total_target - done
    
    # Also verify distinct models used
    cur.execute("""
        SELECT ai_model, COUNT(*) 
        FROM sc_decided_cases 
        WHERE id = ANY(%s)
        GROUP BY ai_model
    """, (target_ids,))
    
    model_breakdown = cur.fetchall()
    
    print(f"\n--- BATCH STATUS ---")
    print(f"Done:      {done} ({done/total_target*100:.1f}%)")
    print(f"Remaining: {remaining}")
    print(f"\nModel Breakdown:")
    for model, count in model_breakdown:
        print(f"  - {model}: {count}")
    
    conn.close()

if __name__ == "__main__":
    report_status()
