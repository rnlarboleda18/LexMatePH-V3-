import psycopg2

DB_URL = "postgresql://bar_admin:[DB_PASSWORD]@bar-db-eu-west.postgres.database.azure.com:5432/postgres?sslmode=require"

def main():
    print("Connecting to Cloud DB...")
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # Hardcoded known typos
    typos = {
        "Evidence defi ned": "Evidence defined",
        "Testimony confi ned to personal knowledge": "Testimony confined to personal knowledge",
        "Unaccepted off er": "Unaccepted offer"
    }

    fixed_count = 0
    for orig, fixed in typos.items():
        print(f"Applying fix: {orig!r} -> {fixed!r}")
        cur.execute("UPDATE roc_codal SET article_title = %s, updated_at = NOW() WHERE article_title = %s", (fixed, orig))
        fixed_count += cur.rowcount

    conn.commit()
    print(f"\n🎉 Successfully hardcoded-fixed {fixed_count} matching Title rows in Cloud!")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
