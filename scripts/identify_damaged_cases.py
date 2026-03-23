import psycopg2
import os

DB_CONNECTION_STRING = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"

def identify_damage():
    try:
        file_path = "target_largest_10.txt"
        if not os.path.exists(file_path):
            print(f"Error: {file_path} not found.")
            return

        with open(file_path, "r") as f:
            ids = [line.strip() for line in f if line.strip()]
            
        if not ids:
            print("No IDs to check.")
            return
            
        conn = psycopg2.connect(DB_CONNECTION_STRING)
        cur = conn.cursor()
        
        id_list_str = ",".join(ids)
        query = f"SELECT id, short_title, ai_model, updated_at FROM sc_decided_cases WHERE id IN ({id_list_str})"
        
        cur.execute(query)
        rows = cur.fetchall()
        
        print("\n--- AFFECTED CASES (Updated to Gemini 2.5 Flash Lite) ---")
        affected_count = 0
        for row in rows:
            cid = row[0]
            title = row[1]
            model = row[2]
            updated = row[3]
            
            if model == 'gemini-2.5-flash-lite':
                print(f"ID: {cid} | Title: {title} | Model: {model} | Updated: {updated}")
                affected_count += 1
            else:
                 # Optional: print others to separate them
                 # print(f"ID: {cid} (Safe - Model: {model})")
                 pass
        
        print(f"\nTotal Affected Cases: {affected_count}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    identify_damage()
