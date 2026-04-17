import psycopg2, json
from pathlib import Path

def verify():
    settings = Path('api/local.settings.json')
    cs = json.loads(settings.read_text()).get('Values', {}).get('DB_CONNECTION_STRING')
    conn = psycopg2.connect(cs)
    cur = conn.cursor()

    # Get RPC code_id
    cur.execute("SELECT code_id FROM legal_codes WHERE short_name = 'RPC'")
    code_id = cur.fetchone()[0]
    print(f"RPC UUID: {code_id}")

    print("\n--- Checking rpc_codal for Art 329 ---")
    cur.execute("SELECT id, article_num, amendments, article_title FROM rpc_codal WHERE article_num = '329'")
    row = cur.fetchone()
    if row:
        print(f"ID: {row[0]}")
        print(f"Article: {row[1]}")
        print(f"Title: {row[3]}")
        print(f"Amendments Column: {row[2]}")
    else:
        print("Article 329 not found in rpc_codal")

    print("\n--- Checking article_versions for Art 329 ---")
    cur.execute("""
        SELECT version_id, amendment_id, valid_from, valid_to 
        FROM article_versions 
        WHERE article_number = '329' 
        AND code_id = %s 
        ORDER BY valid_from ASC
    """, (code_id,))
    rows = cur.fetchall()
    if not rows:
        print("No versions found in article_versions")
    for r in rows:
        print(f"VersionID: {r[0]}, Law: {r[1]}, From: {r[2]}, To: {r[3]}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    verify()
