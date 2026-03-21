import psycopg2
import json
import datetime
import time
import os
import sys

def get_db_connection():
    # Load settings mostly for the internal runs, but let's try standard env first or fall back
    try:
        with open('local.settings.json') as f:
            settings = json.load(f)
            conn_str = settings['Values']['DB_CONNECTION_STRING']
    except:
         # Fallback default
         conn_str = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"
    return psycopg2.connect(conn_str)

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    target_file = 'grok_phase3_ids.txt'
    if not os.path.exists(target_file):
        print(f"Error: {target_file} not found.")
        return

    with open(target_file, 'r') as f:
        ids = [x.strip() for x in f.read().strip().split(',') if x.strip()]
        total_cases = len(ids)

    # Convert to int list once
    int_ids = [int(x) for x in ids if x.isdigit()]
    
    # Start time (Phase 3 approx 23:15)
    start_time = datetime.datetime.now().replace(hour=23, minute=15, second=0, microsecond=0)
    # Handle midnight wrap if needed generally, but for today it's fine.
    
    print(f"Starting Live Monitor for {total_cases} cases...")
    print("Press Ctrl+C to stop.")
    time.sleep(2)

    while True:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Count completed
            query = """
                SELECT count(*) 
                FROM sc_decided_cases 
                WHERE id = ANY(%s) 
                AND ai_model = 'grok-4-1-fast-reasoning'
            """
            cur.execute(query, (int_ids,))
            completed = cur.fetchone()[0]
            conn.close()

            # Calc
            now = datetime.datetime.now()
            if now < start_time: start_time = now # Safety
            
            elapsed_minutes = (now - start_time).total_seconds() / 60.0
            if elapsed_minutes < 0.1: elapsed_minutes = 0.1
            
            rate = completed / elapsed_minutes
            pct = (completed / total_cases) * 100
            remaining = total_cases - completed
            
            etf_str = "N/A"
            if rate > 0:
                etf_min = remaining / rate
                etf_time = now + datetime.timedelta(minutes=etf_min)
                etf_str = etf_time.strftime("%I:%M %p")

            # Display
            clear_screen()
            print("========================================")
            print("   GROK PHASE 3 LIVE MONITOR    ")
            print("========================================")
            print(f"Time:       {now.strftime('%H:%M:%S')}")
            print(f"Total:      {total_cases}")
            print(f"Completed:  {completed}")
            print(f"Remaining:  {remaining}")
            print(f"Progress:   {pct:.2f}%")
            print("----------------------------------------")
            print(f"Speed:      {rate:.2f} cases/min")
            print(f"ETF:        {etf_str}")
            print("========================================")
            print("Updates every 60 seconds...")
            
            time.sleep(60)
            
        except KeyboardInterrupt:
            print("\nMonitor stopped.")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
