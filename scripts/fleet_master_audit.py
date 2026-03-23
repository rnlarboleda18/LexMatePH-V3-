import psycopg2
import json
import time
from datetime import datetime, timedelta

def get_db_connection():
    try:
        with open('local.settings.json', 'r') as f:
            settings = json.load(f)
        return psycopg2.connect(settings['Values']['DB_CONNECTION_STRING'])
    except:
        return psycopg2.connect("postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db")

def get_file_ids(filename):
    try:
        with open(filename, 'r') as f:
            return [int(line.strip()) for line in f if line.strip().isdigit()]
    except:
        return []

def audit_fleet():
    conn = get_db_connection()
    cur = conn.cursor()

    fleets = [
        ("Ghost 1 (<50K)", "ghost_tier_1.txt", "ai_model IS NOT NULL", "gemini-2.5-flash"),
        ("Ghost 2 (50-100K)", "ghost_tier_2.txt", "ai_model IS NOT NULL", "gemini-2.5-pro"),
        ("Ghost 3 (>100K)", "ghost_tier_3.txt", "ai_model IS NOT NULL", "gemini-2.5-pro"),
        ("Significance", "backfill_significance_ids.txt", "digest_significance IS NOT NULL AND digest_significance != '' AND digest_significance != 'Unknown'", "gemini-2.5-flash"),
        ("General BF", "backfill_general_ids.txt", """digest_facts IS NOT NULL AND digest_issues IS NOT NULL AND digest_ruling IS NOT NULL AND digest_ratio IS NOT NULL AND keywords IS NOT NULL AND flashcards IS NOT NULL AND spoken_script IS NOT NULL AND spoken_script != ''""", "gemini-2.5-flash-lite")
    ]

    report = []
    total_target = 0
    total_done = 0

    # Get recent speed (Global)
    cur.execute("SELECT COUNT(*) FROM sc_decided_cases WHERE updated_at > NOW() - INTERVAL '15 minutes'")
    recent_saves_15 = cur.fetchone()[0]
    speed_per_hour = recent_saves_15 * 4

    for name, filename, condition, model in fleets:
        ids = get_file_ids(filename)
        target = len(ids)
        if target == 0: continue
        
        total_target += target
        
        cur.execute(f"SELECT COUNT(*) FROM sc_decided_cases WHERE id = ANY(%s) AND {condition}", (ids,))
        done_count = cur.fetchone()[0]
        total_done += done_count
        
        progress = (done_count / target * 100) if target > 0 else 0
        remaining = target - done_count
        
        report.append({
            "fleet": name,
            "target": target,
            "done": done_count,
            "progress": f"{progress:.1f}%",
            "remaining": remaining,
            "model": model
        })

    conn.close()
    
    overall_pct = (total_done / total_target * 100) if total_target > 0 else 0
    
    # Calculate ETF (Simplified)
    etf_minutes = ( (total_target - total_done) / speed_per_hour * 60 ) if speed_per_hour > 0 else 0
    etf_str = f"{int(etf_minutes // 60)}h {int(etf_minutes % 60)}m" if etf_minutes > 0 else "N/A (Ramping...)"

    return {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "fleets": report,
        "overall": {
            "total_done": total_done,
            "total_target": total_target,
            "overall_progress": f"{overall_pct:.1f}%",
            "global_speed": f"{speed_per_hour} cases/hr",
            "etf": etf_str
        }
    }

if __name__ == "__main__":
    results = audit_fleet()
    print(json.dumps(results, indent=2))
