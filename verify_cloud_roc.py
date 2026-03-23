import psycopg2

# Cloud connection string
CLOUD_DB = "postgresql://bar_admin:[DB_PASSWORD]@bar-db-eu-west.postgres.database.azure.com:5432/postgres?sslmode=require"

def verify_cloud_data():
    print("Connecting to CLOUD DB for verification...")
    conn = psycopg2.connect(CLOUD_DB)
    cur = conn.cursor()

    try:
        # Check column names
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'roc_codal'
            ORDER BY ordinal_position
        """)
        columns = [row[0] for row in cur.fetchall()]
        print(f"Current columns (roc_codal): {', '.join(columns)}")

        # Check total count
        cur.execute("SELECT COUNT(*) FROM roc_codal")
        count = cur.fetchone()[0]
        print(f"Total rows in roc_codal: {count}")

        # Check sample rows for groups and source_ref
        cur.execute("""
            SELECT rule_num, section_num, group_1_title, group_2_title, source_ref, substr(section_content, 1, 50) 
            FROM roc_codal 
            WHERE group_1_title IS NOT NULL OR source_ref IS NOT NULL
            LIMIT 10
        """)
        rows = cur.fetchall()
        print("\nSample Data (Groups & Source Ref):")
        for r in rows:
            print(f"Rule {r[0]}, Sec {r[1]} | G1: {r[2]} | G2: {r[3]} | Ref: {r[4]} | Content: {r[5]}...")

        # Check article_versions count
        cur.execute("SELECT COUNT(*) FROM article_versions WHERE amendment_id = 'ROC'")
        v_count = cur.fetchone()[0]
        print(f"\nTotal rows in article_versions (ROC): {v_count}")

    except Exception as e:
        print(f"Error during verification: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    verify_cloud_data()
