import psycopg2
import os
import time
from datetime import datetime
import sys

DB_CONNECTION_STRING = "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_stats():
    try:
        conn = psycopg2.connect(DB_CONNECTION_STRING)
        cur = conn.cursor()

        # 1. TOTALS
        cur.execute("SELECT COUNT(*) FROM sc_decided_cases")
        total_cases = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM sc_decided_cases WHERE full_text_md IS NOT NULL AND full_text_md != ''")
        ingested_cases = cur.fetchone()[0]
        
        # 2. STATUS COUNTS
        cur.execute("SELECT COUNT(*) FROM sc_decided_cases WHERE digest_significance IS NOT NULL AND digest_significance NOT ILIKE '%PROCESSING%' AND digest_significance != 'BLOCKED_SAFETY'")
        completed = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM sc_decided_cases WHERE digest_significance ILIKE '%PROCESSING%'")
        processing = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM sc_decided_cases WHERE digest_significance = 'BLOCKED_SAFETY'")
        blocked = cur.fetchone()[0]
        
        # 3. DOCTRINAL STATUS
        cur.execute("SELECT COUNT(*) FROM sc_decided_cases WHERE is_doctrinal = TRUE")
        doctrinal_total = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM sc_decided_cases WHERE is_doctrinal = TRUE AND digest_significance IS NOT NULL AND digest_significance NOT ILIKE '%PROCESSING%'")
        doctrinal_completed = cur.fetchone()[0]

        # 4. FIELD HEALTH (Sample key fields)
        cur.execute("SELECT COUNT(*) FROM sc_decided_cases WHERE digest_facts IS NOT NULL AND digest_facts != ''")
        has_facts = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM sc_decided_cases WHERE digest_issues IS NOT NULL AND digest_issues != ''")
        has_issues = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM sc_decided_cases WHERE digest_significance IS NOT NULL AND digest_significance != ''")
        has_intro = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM sc_decided_cases WHERE ai_model IS NOT NULL")
        has_model = cur.fetchone()[0]

        conn.close()

        # CALCULATIONS
        scope = ingested_cases
        remaining = scope - completed - blocked - processing 
        if remaining < 0: remaining = 0
        
        pct_complete = (completed / scope) * 100 if scope > 0 else 0
        pct_doctrinal = (doctrinal_completed / doctrinal_total) * 100 if doctrinal_total > 0 else 0
        
        # ESTIMATE ETF
        # Rate assumption: 150 workers approx 400 cases/min effective
        rate_per_min = 400 
        minutes_left = remaining / rate_per_min if rate_per_min > 0 else 0
        hours_left = minutes_left / 60

        print(f"--- FLEET STATISTICS @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
        print(f"[PROGRESS OVERVIEW]")
        print(f"Total Database Cases: {total_cases}")
        print(f"Ingested (Scope):     {ingested_cases}")
        print(f"✅ Completed:          {completed} ({pct_complete:.2f}%)")
        print(f"🔄 In Progress:        {processing} (Active Workers)")
        print(f"⛔ Blocked/Safety:     {blocked}")
        print(f"⏳ Remaining:          {remaining}")

        print(f"\n[DOCTRINAL CASES]")
        print(f"Total Doctrinal:      {doctrinal_total}")
        print(f"Completed:            {doctrinal_completed} ({pct_doctrinal:.2f}%)")

        print(f"\n[FIELD COMPLETION RATES]")
        print(f"Facts:                {has_facts}")
        print(f"Issues:               {has_issues}")
        print(f"Significance:         {has_intro}")
        print(f"AI Model Tagged:      {has_model}")

        print(f"\n[ESTIMATES]")
        print(f"Active Workers:       ~150")
        print(f"Est. Speed:           ~{rate_per_min} cases/min")
        if hours_left < 1:
            print(f"ETF:                  {minutes_left:.1f} Minutes")
        else:
            print(f"ETF:                  {hours_left:.1f} Hours")
        print("-" * 50)
        sys.stdout.flush()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    try:
        while True:
            clear_screen()
            get_stats()
            print("Next update in 10 minutes... (Press Ctrl+C to stop)")
            time.sleep(600)
    except KeyboardInterrupt:
        print("\nStatistics monitor stopped.")
