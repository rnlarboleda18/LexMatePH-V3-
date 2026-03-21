import psycopg2
import json
from datetime import datetime, timedelta

def deep_audit():
    try:
        with open('local.settings.json', 'r') as f:
            settings = json.load(f)
        conn = psycopg2.connect(settings['Values']['DB_CONNECTION_STRING'])
        cur = conn.cursor()
        
        print("=== DEEP FLEET AUDIT REPORT ===")
        print(f"Start Time: {datetime.now()}")
        print("-" * 30)

        # 1. Recent Saves Summary (Last 5 minutes)
        five_mins_ago = datetime.now() - timedelta(minutes=5)
        cur.execute("""
            SELECT ai_model, COUNT(*) 
            FROM sc_decided_cases 
            WHERE updated_at > %s 
            GROUP BY ai_model
        """, (five_mins_ago,))
        recent_saves = cur.fetchall()
        print("\n[Last 5 Minutes Activity]")
        if recent_saves:
            for model, count in recent_saves:
                print(f" - {model:25}: {count} cases saved")
        else:
            print(" - No saves detected in the last 5 minutes.")

        # 2. Content Density Check (Last 5 cases)
        print("\n[Content Integrity Check - Last 5 Successes]")
        cur.execute("""
            SELECT id, ai_model, updated_at, 
                   LENGTH(COALESCE(digest_facts, '')) as flen,
                   LENGTH(COALESCE(digest_ruling, '')) as rlen,
                   LENGTH(COALESCE(spoken_script, '')) as slen
            FROM sc_decided_cases 
            WHERE updated_at > %s 
            ORDER BY updated_at DESC LIMIT 5
        """, (five_mins_ago,))
        samples = cur.fetchall()
        for s in samples:
            print(f" - Case {s[0]} ({s[1]}): Facts={s[3]} chars, Ruling={s[4]} chars, Script={s[5]} chars")

        # 3. Active Locks (Currently digesting)
        cur.execute("""
            SELECT ai_model, COUNT(*) 
            FROM sc_decided_cases 
            WHERE digest_significance = 'PROCESSING'
            GROUP BY ai_model
        """)
        locks = cur.fetchall()
        print("\n[Active Processing Locks (Live digestion)]")
        if locks:
            for model, count in locks:
                print(f" - {model:25}: {count} active workers")
        else:
            print(" - No active locks (IDLE).")

        # 4. Error Check (Recent NULLs or Blocks)
        cur.execute("""
            SELECT digest_significance, COUNT(*) 
            FROM sc_decided_cases 
            WHERE updated_at > %s AND digest_significance IN ('BLOCKED_SAFETY', 'ERROR')
            GROUP BY digest_significance
        """, (five_mins_ago,))
        errors = cur.fetchall()
        print("\n[Recent Failure States]")
        if errors:
            for state, count in errors:
                print(f" - {state:25}: {count} cases")
        else:
            print(" - No blocks/errors in last 5 minutes.")

        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    deep_audit()
