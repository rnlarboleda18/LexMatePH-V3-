import psycopg2
import json

def get_db_connection():
    try:
        with open('api/local.settings.json') as f:
            settings = json.load(f)
            conn_str = settings['Values']['DB_CONNECTION_STRING']
    except Exception:
        conn_str = "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"
    return psycopg2.connect(conn_str)

def create_table():
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS roc_codal (
                id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
                book integer,
                title_num integer,
                title_label text,
                chapter_label text,
                article_num text,
                article_suffix character,
                article_title text,
                content_md text,
                elements jsonb,
                amendments jsonb,
                updated_at timestamp without time zone DEFAULT now(),
                chapter_num integer,
                book_label text,
                section_num integer,
                section_label text,
                chapter text,
                structural_map jsonb,
                created_at timestamp with time zone DEFAULT now()
            );
        """)
        conn.commit()
        print("Table roc_codal created successfully.")
    except Exception as e:
        conn.rollback()
        print(f"Error creating table: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    create_table()
