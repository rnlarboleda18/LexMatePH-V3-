import psycopg2

DB_URL = "postgresql://bar_admin:[DB_PASSWORD]@bar-db-eu-west.postgres.database.azure.com:5432/postgres?sslmode=require"

def main():
    print("Connecting to Cloud DB...")
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    print("Updating header rows fully clearing `article_num`...")
    cur.execute("""
        UPDATE roc_codal 
        SET article_num = '' 
        WHERE article_num LIKE '%Header' 
           OR article_num LIKE '%Subheader'
    """)
    updated = cur.rowcount
    
    conn.commit()
    print(f"🎉 Successfully cleared `article_num` for {updated} header rows on Cloud!")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
