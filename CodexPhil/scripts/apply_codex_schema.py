import psycopg2
import json
import os

def get_db_connection():
    try:
        with open('local.settings.json') as f:
            settings = json.load(f)
            conn_str = settings['Values']['DB_CONNECTION_STRING']
    except Exception as e:
        print(f"Warning: Could not read local.settings.json: {e}")
        conn_str = "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"
    return psycopg2.connect(conn_str)

def apply_schema():
    print("Applying Codex Philippine Schema...")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        with open('scripts/codex_init.sql', 'r') as f:
            sql_script = f.read()
            
        cur.execute(sql_script)
        conn.commit()
        print("Schema applied successfully.")
        
        # Verify creation
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        tables = [row[0] for row in cur.fetchall()]
        
        required = ['legal_codes', 'article_versions', 'jurisprudence_links']
        missing = [t for t in required if t not in tables]
        
        if missing:
            print(f"ERROR: Missing tables: {missing}")
        else:
            print("VERIFICATION: All required tables found.")
            
    except Exception as e:
        print(f"Error applying schema: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    apply_schema()
