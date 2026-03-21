import psycopg2
from api.db_pool import DB_CONNECTION_STRING

def check_tables():
    print("Connecting to:", DB_CONNECTION_STRING.split('@')[1])
    try:
        conn = psycopg2.connect(DB_CONNECTION_STRING)
        cur = conn.cursor()
        
        # 1. List all tables
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = [r[0] for r in cur.fetchall()]
        print("\n=== Tables in Cloud DB ===")
        for t in tables:
            print(f"- {t}")
            
        # 2. Check row counts for key codal tables
        checks = ['rpc_codal', 'civ_codal', 'consti_codal', 'fc_codal', 'roc_codal', 'sc_decisions']
        print("\n=== Row Counts ===")
        for t in checks:
            if t in tables:
                cur.execute(f"SELECT COUNT(*) FROM {t}")
                count = cur.fetchone()[0]
                print(f"{t}: {count} rows")
            else:
                print(f"{t}: MISSING")
                
        cur.close()
        conn.close()
    except Exception as e:
        print("Error:", str(e))

if __name__ == "__main__":
    check_tables()
