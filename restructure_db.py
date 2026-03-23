import psycopg2

DB_CONNECTION = "dbname=lexmateph-ea-db user=postgres password=b66398241bfe483ba5b20ca5356a87be host=localhost port=5432"

def restructure_db():
    conn = psycopg2.connect(DB_CONNECTION)
    cur = conn.cursor()
    
    try:
        # Delete old Constitution records. We protect Family Code entries which start with 'FC-'.
        # We also want to protect PREAMBLE or Article headers, but wait, those should be deleted too so we can re-ingest them cleanly.
        # "Delete the present sonstitutional codals entiresly"
        cur.execute("DELETE FROM const_codal WHERE article_num NOT LIKE 'FC-%';")
        deleted_count = cur.rowcount
        print(f"Deleted {deleted_count} Constitution records.")
        
        # Alter schema to add new columns if they don't exist
        cur.execute("ALTER TABLE const_codal ADD COLUMN IF NOT EXISTS group_header text;")
        cur.execute("ALTER TABLE const_codal ADD COLUMN IF NOT EXISTS book_code text;")
        
        conn.commit()
        print("Schema altered successfully (added group_header, book_code).")
        
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    restructure_db()
