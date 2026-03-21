import psycopg2
import time
import os
import json

def get_db_connection():
    try:
        with open('local.settings.json', 'r') as f:
            settings = json.load(f)
        return psycopg2.connect(settings['Values']['DB_CONNECTION_STRING'])
    except:
        return psycopg2.connect("postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local")

def get_progress():
    try:
        # Load the ghost list to know the target IDs
        ghost_file = 'ghost_fleet_combined.txt'
        if not os.path.exists(ghost_file):
            return 0, 1219 # Fallback to known target
            
        with open(ghost_file, 'r') as f:
            target_ids = [line.strip() for line in f if line.strip()]
        
        target_count = len(target_ids)
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check how many of these specific IDs have a non-null ai_model or are recently updated
        # Actually, the 'Combined Ghost' criteria is usually cases that NEEDED work.
        # We track completion by seeing which of these IDs currently have the expected fields.
        # For simplicity, we'll check ai_model for these IDs.
        cur.execute("SELECT COUNT(*) FROM sc_decided_cases WHERE id = ANY(%s) AND ai_model IS NOT NULL", (target_ids,))
        done_count = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        return done_count, target_count
    except Exception as e:
        print(f"Error: {e}")
        return 0, 0

def main():
    print("Starting Live Ghost Fleet Monitor (Ctrl+C to stop)")
    print("-" * 40)
    try:
        while True:
            done, target = get_progress()
            pct = (done / target * 100) if target > 0 else 0
            
            timestamp = time.strftime('%H:%M:%S')
            print(f"[{timestamp}] Progress: {done}/{target} ({pct:.1f}%) | Remaining: {target-done}")
            
            time.sleep(30) # Refresh every 30 seconds for the user
    except KeyboardInterrupt:
        print("\nMonitor stopped.")

if __name__ == "__main__":
    main()
