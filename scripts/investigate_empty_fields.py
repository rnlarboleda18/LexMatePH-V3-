import psycopg2
import os
import json

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

def investigate():
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()
    
    print("--- INVESTIGATING 10 SAMPLE 'EMPTY FACTS' CASES ---")
    
    # Query: Has AI Model (supposedly processed) but NO Facts
    query = """
        SELECT id, title, ai_model, updated_at, digest_significance 
        FROM sc_decided_cases 
        WHERE ai_model IS NOT NULL 
          AND digest_facts IS NULL
        LIMIT 10
    """
    
    cur.execute(query)
    rows = cur.fetchall()
    
    if not rows:
        print("No cases found matching criteria.")
        return

    print(f"{'ID':<10} | {'Model':<20} | {'Updated At':<25} | {'Significance'}")
    print("-" * 80)
    for row in rows:
        id_ = row[0]
        title = (row[1][:30] + '...') if row[1] else 'No Title'
        model = row[2]
        updated = str(row[3])
        sig = str(row[4])[:20]
        
        print(f"{id_:<10} | {model:<20} | {updated:<25} | {sig}")
    
    print("-" * 80)
    
    # Also check stats on which models are guilty
    print("\n--- MODEL BREAKDOWN FOR EMPTY FACTS ---")
    
    stats_query = """
        SELECT ai_model, COUNT(*) 
        FROM sc_decided_cases 
        WHERE digest_facts IS NULL AND ai_model IS NOT NULL
        GROUP BY ai_model
        ORDER BY COUNT(*) DESC
    """
    cur.execute(stats_query)
    stats = cur.fetchall()
    
    for model, count in stats:
        print(f"{model}: {count}")

    conn.close()

if __name__ == "__main__":
    investigate()
