import psycopg2
import os

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"

def setup_test():
    try:
        conn = psycopg2.connect(DB_CONNECTION_STRING)
        cur = conn.cursor()
        
        # Check matching for Aniano
        cur.execute("SELECT COUNT(*) FROM sc_decided_cases WHERE short_title ILIKE '%Aniano%'")
        aniano_short = cur.fetchone()[0]
        print(f"Aniano in Short Title: {aniano_short}")

        # Update ID 39842 with Unique Tokens
        # Full Title -> "TIER_TWO_UNIQUE_KEY"
        # Body -> "TIER_THREE_UNIQUE_KEY"
        
        cur.execute("""
            UPDATE sc_decided_cases 
            SET full_title = 'The People vs. TIER_TWO_UNIQUE_KEY',
                full_text_md = 'This is the body content containing TIER_THREE_UNIQUE_KEY for testing.'
            WHERE id = 39842
        """)
        conn.commit()
        print("Injected Unique Tokens into ID 39842.")
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    setup_test()
