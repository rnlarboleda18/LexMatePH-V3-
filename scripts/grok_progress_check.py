import psycopg2
import json
import datetime
import sys

def get_db_connection():
    with open('local.settings.json') as f:
        settings = json.load(f)
        conn_str = settings['Values']['DB_CONNECTION_STRING']
    return psycopg2.connect(conn_str)

def main():
    # 1. Load Total Target IDs
    target_file = 'grok_phase3_ids.txt'
    try:
        with open(target_file, 'r') as f:
            ids = [x.strip() for x in f.read().strip().split(',') if x.strip()]
            total_cases = len(ids)
    except FileNotFoundError:
        print(f"Error: {target_file} not found.")
        return

    # 2. DB Query for Completed Count (Phase 3)
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Check how many have been converted to the new model
    query = """
        SELECT count(*) 
        FROM sc_decided_cases 
        WHERE id = ANY(%s) 
        AND ai_model = 'grok-4-1-fast-reasoning'
    """
    # Cast to int list for Postgres
    int_ids = [int(x) for x in ids if x.isdigit()]
    
    cur.execute(query, (int_ids,))
    completed = cur.fetchone()[0]
    conn.close()

    # 3. Calculate Stats
    # Phase 3 Launch approx 23:15
    start_time = datetime.datetime.now().replace(hour=23, minute=15, second=0, microsecond=0)
    
    now = datetime.datetime.now()
    if now < start_time: start_time = now

    elapsed_minutes = (now - start_time).total_seconds() / 60.0
    if elapsed_minutes < 0.1: elapsed_minutes = 0.1
    
    rate_per_min = completed / elapsed_minutes
    percentage = (completed / total_cases) * 100
    remaining = total_cases - completed
    
    if rate_per_min > 0:
        etf_minutes = remaining / rate_per_min
        etf_time = now + datetime.timedelta(minutes=etf_minutes)
        etf_str = etf_time.strftime("%H:%M:%S")
    else:
        etf_minutes = 0
        etf_str = "N/A"

    # 4. output
    print(f"--- Grok Progress Update ---")
    print(f"Time: {now.strftime('%H:%M:%S')}")
    print(f"Progress: {completed}/{total_cases} ({percentage:.2f}%)")
    print(f"Speed: {rate_per_min:.2f} cases/min")
    print(f"Remaining: {remaining}")
    print(f"ETF: {etf_str}")
    print(f"----------------------------")

if __name__ == "__main__":
    main()
