import psycopg2
import os

DB_CONNECTION_STRING = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"

def get_largest_non_compliant():
    try:
        # Read the IDs from the file
        file_path = "non_compliant_digest_ids.txt"
        if not os.path.exists(file_path):
            print(f"Error: {file_path} not found.")
            return

        with open(file_path, "r") as f:
            ids = [line.strip() for line in f if line.strip()]
        
        if not ids:
            print("No IDs found in file.")
            return
            
        print(f"Loaded {len(ids)} IDs. Querying database for sizes...")
        
        conn = psycopg2.connect(DB_CONNECTION_STRING)
        cur = conn.cursor()
        
        # We need to query in chunks if the list is huge, but 7k is fine for a single IN clause usually, 
        # or we can just iterate. Let's do a bulk query for efficiency.
        # Postgres IN limit is high, but let's be safe and do chunks of 1000 or just fetch lengths for these IDs.
        
        # Actually, let's just fetch id and length(full_text_md) for ALL cases in the list.
        # Constructing a massive IN clause might be slow. 
        # Better approach: Create a temporary table or value list.
        
        id_list_str = ",".join(ids)
        
        # Danger: huge query string. Let's filter on the DB side if possible?
        # Alternatively, we iterate results.
        
        # Let's try passing as tuple if not too huge. 7000 IDs is about 50KB query string. It's fine for Postgres.
        
        query = f"""
            SELECT id, COALESCE(length(full_text_md), 0) as len 
            FROM sc_decided_cases 
            WHERE id IN ({id_list_str})
            ORDER BY len DESC
            LIMIT 10
        """
        
        cur.execute(query)
        rows = cur.fetchall()
        
        print("\n--- TOP 10 LARGEST NON-COMPLIANT CASES ---")
        top_10_ids = []
        for row in rows:
            print(f"ID: {row[0]}, Length: {row[1]}")
            top_10_ids.append(str(row[0]))
            
        with open("target_largest_10.txt", "w") as f:
            for tid in top_10_ids:
                f.write(f"{tid}\n")
        
        print("\nSaved Top 10 IDs to target_largest_10.txt")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    get_largest_non_compliant()
