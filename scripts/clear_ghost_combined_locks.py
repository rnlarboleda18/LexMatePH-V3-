import psycopg2
import json
import os

def get_db_connection():
    db_connection_string = "postgresql://postgres:password@localhost:5432/sc_decisions"
    try:
        possible_paths = [
            'api/local.settings.json', 
            '../api/local.settings.json',
            'local.settings.json'
        ]
        settings = None
        for path in possible_paths:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    settings = json.load(f)
                break
        if settings:
            db_connection_string = settings['Values']['DB_CONNECTION_STRING']
    except Exception as e:
        print(f"Warning loading settings: {e}")
    return psycopg2.connect(db_connection_string)

def main():
    try:
        print("Clearing Combined Ghost Fleet locks...")
        fleet_file = 'ghost_fleet_combined.txt'
        if not os.path.exists(fleet_file) and os.path.exists('scripts/ghost_fleet_combined.txt'):
            fleet_file = 'scripts/ghost_fleet_combined.txt'
            
        if not os.path.exists(fleet_file):
            print("Fleet file not found!")
            return

        with open(fleet_file, 'r', encoding='utf-8-sig') as f:
            ids = [line.strip() for line in f if line.strip()]
        
        # Clean IDs
        clean_ids = []
        for i in ids:
            try: clean_ids.append(int(i))
            except: pass
            
        if not clean_ids:
            print("No IDs found.")
            return

        conn = get_db_connection()
        cur = conn.cursor()
        
        # Convert to tuple for SQL
        ids_tuple = tuple(clean_ids)
        
        # RESET LOCKS: Set digest_significance to NULL where it is 'PROCESSING'
        cur.execute("""
            UPDATE sc_decided_cases 
            SET digest_significance = NULL 
            WHERE id IN %s 
              AND digest_significance = 'PROCESSING'
        """, (ids_tuple,))
        
        count = cur.rowcount
        conn.commit()
        conn.close()
        
        print(f"✅ Successfully cleared locks for {count} cases.")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
