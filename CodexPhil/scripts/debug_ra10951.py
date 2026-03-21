import psycopg2
import json

def get_db_connection():
    try:
        with open('local.settings.json') as f:
            settings = json.load(f)
            conn_str = settings['Values']['DB_CONNECTION_STRING']
    except Exception:
        conn_str = "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"
    return psycopg2.connect(conn_str)

conn = get_db_connection()
cur = conn.cursor()

code_id = "e87df332-2d1b-4d44-be1a-da35f47055c6" # RPC code ID (I'll fetch it dynamically to be safe)
cur.execute("SELECT code_id FROM legal_codes WHERE short_name = 'RPC'")
code_id = cur.fetchone()[0]
print(f"Code ID: {code_id}")

article_num = "115"
amendment_id = "Republic Act No. 10951"
amendment_date = "2017-08-29"
new_content = "Test content for RA 10951 debugging."

print("Attempting DB update...")
try:
    # Step 1: Close current
    print("Closing old version...")
    cur.execute("""
        UPDATE article_versions
        SET valid_to = %s
        WHERE code_id = %s
            AND article_number = %s
            AND valid_to IS NULL
    """, (amendment_date, code_id, article_num))
    
    # Step 2: Insert new
    print("Inserting new version...")
    cur.execute("""
        INSERT INTO article_versions
        (code_id, article_number, content, valid_from, valid_to, amendment_id)
        VALUES (%s, %s, %s, %s, NULL, %s)
    """, (code_id, article_num, new_content, amendment_date, amendment_id))
    
    conn.commit()
    print("Success!")
except Exception as e:
    conn.rollback()
    print(f"FAILED: {e}")

conn.close()
