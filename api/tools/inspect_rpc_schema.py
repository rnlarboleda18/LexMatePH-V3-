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

def inspect_schema():
    conn = get_db_connection()
    cur = conn.cursor()
    
    tables = ['rpc_codal', 'civ_codal', 'const_codal']
    
    for table in tables:
        print(f"\n--- Schema for {table} ---")
        cur.execute(f"""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = '{table}'
            ORDER BY ordinal_position;
        """)
        columns = cur.fetchall()
        for col in columns:
            print(f"{col[0]} ({col[1]}) - Nullable: {col[2]}")
            
    conn.close()

if __name__ == "__main__":
    inspect_schema()
