import psycopg2

DB_CONNECTION = "postgresql://bar_admin:RABpass021819!@bar-db-eu-west.postgres.database.azure.com:5432/postgres?sslmode=require"

def restructure_db():
    conn = psycopg2.connect(DB_CONNECTION)
    cur = conn.cursor()
    
    try:
        # 1. Rename const_codal to fc_codal
        print("Renaming const_codal to fc_codal...")
        cur.execute("ALTER TABLE const_codal RENAME TO fc_codal;")
        
        # 2. Create consti_codal table
        print("Creating consti_codal table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS consti_codal (
                id SERIAL PRIMARY KEY,
                article_num TEXT,
                article_label TEXT,
                article_title TEXT,
                section_num TEXT,
                section_label TEXT,
                group_header TEXT,
                content_md TEXT,
                list_order INTEGER,
                book_code TEXT DEFAULT 'CONST',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        conn.commit()
        print("Database restructure complete.")
        
    except Exception as e:
        conn.rollback()
        print(f"Error during restructure: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    restructure_db()
