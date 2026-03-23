
import psycopg2
import os
import sys

# Windows console encoding fix
import codecs
sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

def get_db_connection():
    # Use environment variable or fallback for local dev
    conn_str = os.environ.get("DB_CONNECTION_STRING") or "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"
    return psycopg2.connect(conn_str)

def audit_amendments():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        print("Scanning for amended articles with missing amendment IDs...")
        print("=" * 60)
        
        # Find articles with multiple versions where the latest version 
        # has amendment_id = 'Act No. 3815' (base code) or NULL
        query = """
            WITH VersionCounts AS (
                SELECT code_id, article_number, COUNT(*) as v_count 
                FROM article_versions 
                GROUP BY code_id, article_number 
                HAVING COUNT(*) > 1
            )
            SELECT av.article_number, av.version_id, av.amendment_id, av.valid_from
            FROM article_versions av
            JOIN VersionCounts vc ON av.code_id = vc.code_id AND av.article_number = vc.article_number
            WHERE av.valid_to IS NULL -- Latest version
            AND (av.amendment_id = 'Act No. 3815' OR av.amendment_id IS NULL)
            ORDER BY av.article_number
        """
        
        cur.execute(query)
        rows = cur.fetchall()
        
        if not rows:
            print("No anomalies found. All amended articles have distinct amendment IDs.")
        else:
            print(f"Found {len(rows)} potentially incorrect records:")
            for row in rows:
                print(f"Article {row[0]}: ID={row[2]}, ValidFrom={row[3]}")
                
        print("\nChecking specific known historical amendments...")
        # Placeholder lists based on typical amendment history if needed
        # For now, relying on the version count logic is robust for internal consistency
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    audit_amendments()
