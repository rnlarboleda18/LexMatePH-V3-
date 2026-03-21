import psycopg2
import os

def run_migration():
    conn_str = os.environ.get("DB_CONNECTION_STRING") or "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"
    try:
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor()
        
        print("Running schema update for advanced features...")
        
        # Add new columns
        columns = [
            ("cited_cases", "JSONB"),
            ("statutes_involved", "JSONB"),
            ("flashcards", "JSONB"),
            ("vote_nature", "TEXT"),
            ("spoken_script", "TEXT"),
            ("complexity_score", "INTEGER")
        ]
        
        for col_name, col_type in columns:
            try:
                cur.execute(f"ALTER TABLE supreme_decisions ADD COLUMN IF NOT EXISTS {col_name} {col_type};")
                print(f"Added column: {col_name}")
            except Exception as e:
                print(f"Error adding {col_name}: {e}")
                conn.rollback()
        
        conn.commit()
        print("Schema update complete.")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Connection Error: {e}")

if __name__ == "__main__":
    run_migration()
