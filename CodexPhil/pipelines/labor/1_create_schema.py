import psycopg2
import uuid

DB_CONNECTION = "dbname=bar_reviewer_local user=postgres password=b66398241bfe483ba5b20ca5356a87be host=localhost port=5432"

def create_labor_table():
    conn = psycopg2.connect(DB_CONNECTION)
    cur = conn.cursor()
    
    # Check if table exists
    cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'labor_codal');")
    exists = cur.fetchone()[0]
    
    if not exists:
        print("Creating labor_codal table...")
        cur.execute("""
            CREATE TABLE labor_codal (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                book_code VARCHAR(50) DEFAULT 'LABOR',
                book VARCHAR(50),
                book_label TEXT,
                title_num VARCHAR(50),
                title_label TEXT,
                chapter_num VARCHAR(50),
                chapter_label TEXT,
                article_num VARCHAR(50),
                article_title TEXT,
                content_md TEXT,
                amendments JSONB,
                footnotes JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("Table labor_codal created.")
    else:
        print("Table labor_codal already exists.")
        
        # Ensure footnotes column exists if table was already created
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='labor_codal' AND column_name='footnotes';")
        if not cur.fetchone():
            print("Adding footnotes column to existing table...")
            cur.execute("ALTER TABLE labor_codal ADD COLUMN footnotes JSONB;")
    
    print("Registering LABOR code in statutes table if not exists...")
    # Generate a deterministic UUID or random one
    # We will check if it exists by alias first
    cur.execute("SELECT id FROM statutes WHERE alias = 'LABOR';")
    row = cur.fetchone()
    if not row:
        new_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO statutes (id, alias, full_name, category)
            VALUES (%s, 'LABOR', 'Labor Code of the Philippines (P.D. No. 442)', 'Codal')
        """, (new_id,))
        print("Registration complete.")
    else:
        print("LABOR already registered in statutes.")

    conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    create_labor_table()
