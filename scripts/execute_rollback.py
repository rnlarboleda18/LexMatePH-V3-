import psycopg2
DB_CONNECTION_STRING = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"
conn = psycopg2.connect(DB_CONNECTION_STRING)
cur = conn.cursor()

print("Deleting...")
cur.execute("DELETE FROM sc_decided_cases WHERE scrape_source = 'E-Library Scraper' AND case_number IS NULL")
deleted = cur.rowcount
conn.commit()
print(f"Deleted {deleted} records.")
conn.close()
