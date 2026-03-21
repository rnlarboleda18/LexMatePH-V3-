import psycopg2
import os
import time
import psutil
from datetime import datetime
import sys

# Configuration
DB_CONNECTION_STRING = "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:6432/postgres?sslmode=require"
MODEL_TARGET = "gemini-2.5-flash-lite"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_active_workers():
    """Counts active python processes running the digest script."""
    fleets = {
        "Unified Fleet (1901-2025)": 0,
        "Fill Empty Fleet": 0,
        "Gemini 3 Preview Fleet": 0,
        "Seek & Fill Fleet": 0,
        "Other": 0
    }
    total = 0
    
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if proc.info['name'] in ['python.exe', 'python']:
                cmdline = proc.info['cmdline']
                if cmdline and 'generate_sc_digests_gemini.py' in ' '.join(cmdline):
                    cmd_str = ' '.join(cmdline)
                    total += 1
                    
                    if 'gemini-3-flash-preview' in cmd_str:
                         fleets["Gemini 3 Preview Fleet"] += 1
                    elif '--fill-empty' in cmd_str:
                        fleets["Fill Empty Fleet"] += 1
                    elif '--seek-and-fill' in cmd_str:
                        fleets["Seek & Fill Fleet"] += 1
                    elif '--ascending' in cmd_str or '--start-year' in cmd_str:
                        fleets["Unified Fleet (1901-2025)"] += 1
                    else:
                        fleets["Other"] += 1
    except:
        pass
    return fleets, total

def get_db_counts(cur, start_year, end_year):
    """Get stats for a specific year range."""
    # Scope
    cur.execute(f"SELECT COUNT(*) FROM sc_decided_cases WHERE date BETWEEN '{start_year}-01-01' AND '{end_year}-12-31'")
    total = cur.fetchone()[0]
    
    # Completed (Target Model)
    cur.execute(f"""
        SELECT COUNT(*) FROM sc_decided_cases 
        WHERE date BETWEEN '{start_year}-01-01' AND '{end_year}-12-31'
        AND ai_model = '{MODEL_TARGET}'
    """)
    completed = cur.fetchone()[0]
    
    # Active (Locked)
    cur.execute(f"""
        SELECT COUNT(*) FROM sc_decided_cases 
        WHERE date BETWEEN '{start_year}-01-01' AND '{end_year}-12-31'
        AND digest_significance = 'PROCESSING'
    """)
    active = cur.fetchone()[0]
    
    # Backlog (Not completed, not locked, not blocked)
    # Simplified definition: Total - Completed - Active - Blocked
    cur.execute(f"""
        SELECT COUNT(*) FROM sc_decided_cases 
        WHERE date BETWEEN '{start_year}-01-01' AND '{end_year}-12-31'
        AND digest_significance = 'BLOCKED_SAFETY'
    """)
    blocked = cur.fetchone()[0]
    
    remaining = total - completed - active - blocked
    if remaining < 0: remaining = 0
    
    return total, completed, active, blocked, remaining

def get_db_stats(cur, start_year, end_year, model_target):
    """Get stats for a specific year range, returning a dictionary."""
    # Scope
    cur.execute(f"SELECT COUNT(*) FROM sc_decided_cases WHERE date BETWEEN '{start_year}-01-01' AND '{end_year}-12-31'")
    total = cur.fetchone()[0]

    # Completed (Target Model)
    cur.execute(f"""
        SELECT COUNT(*) FROM sc_decided_cases
        WHERE date BETWEEN '{start_year}-01-01' AND '{end_year}-12-31'
        AND ai_model = '{model_target}'
    """)
    completed = cur.fetchone()[0]

    # Backlog (Not completed, not locked, not blocked)
    # Simplified definition: Total - Completed - Active - Blocked
    cur.execute(f"""
        SELECT COUNT(*) FROM sc_decided_cases
        WHERE date BETWEEN '{start_year}-01-01' AND '{end_year}-12-31'
        AND digest_significance = 'BLOCKED_SAFETY'
    """)
    blocked = cur.fetchone()[0]

    # Active (Locked) is handled separately in the monitor function for now
    # to distinguish between 'active' workers and 'active' DB locks.
    # So, 'remaining' here will be total - completed - blocked.
    # The 'active_locks' will be added to the total_locks in the monitor.
    
    # We need to get the count of 'PROCESSING' cases to subtract from remaining
    cur.execute(f"""
        SELECT COUNT(*) FROM sc_decided_cases
        WHERE date BETWEEN '{start_year}-01-01' AND '{end_year}-12-31'
        AND digest_significance = 'PROCESSING'
    """)
    processing_cases = cur.fetchone()[0]

    remaining = total - completed - blocked - processing_cases
    if remaining < 0: remaining = 0

    return {
        "total": total,
        "done": completed,
        "blocked": blocked,
        "remaining": remaining
    }


def monitor(state=None):
    if state is None:
        state = {'start_time': time.time(), 'start_done': -1}

    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()
    
    fleet_counts, total_workers_os = get_active_workers()
    
    # Calculate Speed
    elapsed = (time.time() - state['start_time']) / 60 # minutes
    
    # DB Stats
    # DB Stats
    counts = get_db_stats(cur, 1901, 2025, "gemini-2.5-flash-lite")
    
    # Active Locks
    cur.execute("SELECT COUNT(*) FROM sc_decided_cases WHERE digest_significance = 'PROCESSING'")
    total_active_locks = cur.fetchone()[0]
    
    if state['start_done'] == -1:
        state['start_done'] = counts['done']
        speed = 0.0
        etf = "Calc..."
    else:
        done_delta = counts['done'] - state['start_done']
        if elapsed > 0.5: # Wait 30s for meaningful speed
             speed = done_delta / elapsed
             if speed > 0:
                 mins_left = counts['remaining'] / speed
                 etf = f"{mins_left:.0f}m"  if mins_left < 180 else f"{mins_left/60:.1f}h"
             else:
                 etf = "Stalled"
        else:
            speed = 0.0
            etf = "Calc..."

    percent = (counts['done'] / counts['total']) * 100

    fleets_config = [
        {"name": "Unified Fleet", "key": "Unified Fleet (1901-2025)"},
        {"name": "Fill Empty", "key": "Fill Empty Fleet"},
        {"name": "Gemini 3 Preview", "key": "Gemini 3 Preview Fleet"},
    ]

    clear_screen()
    print(f"--- FLEET V2 MONITOR @ {datetime.now().strftime('%H:%M:%S')} ---")
    print(f"{'FLEET':<20} | {'WKR':<3} | {'LCK':<5} | {'DONE':<8} | {'LEFT':<8} | {'%':<5} | {'SPD':<8} | {'ETF':<8}")
    print("-" * 80)
    
    for f in fleets_config:
        w_count = fleet_counts.get(f["key"], 0)
        # Display any fleet with active workers
        if w_count > 0:
             print(f"{f['name']:<20} | {w_count:<3} | {'-':<5} | {'-':<8} | {'-':<8} | {'-':<5} | {'-':<8} | {'-':<8}")

    print("-" * 80)
    print(f"{'TOTAL':<20} | {total_workers_os:<3} | {total_active_locks:<5} | {counts['done']:<8} | {counts['remaining']:<8} | {percent:.1f}% | {speed:.1f}/m | {etf:<8}")
    print("-" * 80)
    
    conn.close()
    return state

if __name__ == "__main__":
    monitor_state = None
    while True:
        try:
            monitor_state = monitor(monitor_state)
            time.sleep(60)
        except KeyboardInterrupt:
            print("\nStopping...")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(60)
