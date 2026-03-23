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

def insert_preamble():
    content = """[ Act No. 3815, December 08, 1930 ]

## AN ACT REVISING THE PENAL CODE AND OTHER PENAL LAWS.
Be it enacted by the Senate and House of Representatives of the Philippines inLegislature assembled and by the authority of the same:
PRELIMINARY ARTICLE.-This law shall be known as "The Revised Penal Code."

## BOOK ONE
GENERAL PROVISIONS REGARDING THE DATE OF ENFORCEMENT AND APPLICATION OF THE PROVISIONS OF THIS CODE, AND REGARDING THE OFFENSES, THE PERSONS LIABLE AND THE PENALTIES

## PRELIMINARY TITLE

## DATE OF EFFECTIVENESS AND APPLICATION OF THE PROVISIONS OF THIS CODE"""

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Get Code ID
        cur.execute("SELECT code_id FROM legal_codes WHERE short_name = 'RPC'")
        row = cur.fetchone()
        if not row:
            print("RPC not found")
            return
        
        code_id = row[0]
        
        # Check if 0 exists
        cur.execute("SELECT version_id FROM article_versions WHERE code_id = %s AND article_number = '0'", (code_id,))
        if cur.fetchone():
            print("Article 0 (Preamble) already exists. Updating content...")
            cur.execute("""
                UPDATE article_versions 
                SET content = %s 
                WHERE code_id = %s AND article_number = '0'
            """, (content, code_id))
        else:
            print("Inserting Preamble as Article 0...")
            cur.execute("""
                INSERT INTO article_versions (code_id, article_number, content, valid_from, valid_to, amendment_id)
                VALUES (%s, '0', %s, '1932-01-01', NULL, 'Act No. 3815')
            """, (code_id, content))
        
        conn.commit()
        print("Success.")
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    insert_preamble()
