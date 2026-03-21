import psycopg2
from psycopg2.extras import RealDictCursor

def main():
    try:
        conn = psycopg2.connect("postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local")
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT content_md, article_num FROM roc_codal WHERE article_num = 'Rule 10, Section 1'")
        row = cur.fetchone()
        if row:
             print("--- Rule 10, Section 1 Content ---")
             print(repr(row['content_md']))
        else:
             print("Row not found for Rule 10, Section 1")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
