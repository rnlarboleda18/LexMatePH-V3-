import psycopg2
import json
import os

def get_db_connection():
    try:
        with open('local.settings.json', 'r') as f:
            settings = json.load(f)
        return psycopg2.connect(settings['Values']['DB_CONNECTION_STRING'])
    except:
        return psycopg2.connect("postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local")

def extract_tiers():
    conn = get_db_connection()
    cur = conn.cursor()

    tiers = [
        ("ghost_tier_1.txt", "length(full_text_md) < 50000"),
        ("ghost_tier_2.txt", "length(full_text_md) >= 50000 AND length(full_text_md) < 100000"),
        ("ghost_tier_3.txt", "length(full_text_md) >= 100000")
    ]

    for filename, condition in tiers:
        query = f"SELECT id FROM sc_decided_cases WHERE ai_model IS NULL AND {condition} AND full_text_md IS NOT NULL ORDER BY id ASC"
        cur.execute(query)
        ids = [str(row[0]) for row in cur.fetchall()]
        
        with open(filename, 'w') as f:
            f.write('\n'.join(ids))
        print(f"Exported {len(ids)} IDs to {filename}")

    conn.close()

if __name__ == "__main__":
    extract_tiers()
