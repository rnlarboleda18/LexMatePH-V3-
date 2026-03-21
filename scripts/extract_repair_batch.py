import json
import psycopg
import os

settings = json.load(open('api/local.settings.json'))
conn_str = settings['Values']['DB_CONNECTION_STRING']

def main():
    if not os.path.exists('audit_repair_missing.txt'):
        print("Error: audit_repair_missing.txt not found.")
        return

    with open('audit_repair_missing.txt', 'r') as f:
        ids = [x.strip() for x in f.readlines() if x.strip()]

    print(f"Filtering {len(ids)} cases from audit_repair_missing.txt...")

    target_ids = []
    
    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            # PostgreSQL query to filter by year range
            query = """
                SELECT id
                FROM sc_decided_cases 
                WHERE id = ANY(%s)
                AND EXTRACT(YEAR FROM date) BETWEEN 1901 AND 1986
                ORDER BY date ASC
            """
            
            id_ints = [int(i) for i in ids]
            cur.execute(query, (id_ints,))
            rows = cur.fetchall()
            
            target_ids = [str(r[0]) for r in rows]

    print(f"Found {len(target_ids)} cases between 1901 and 1986.")
    
    # Save to file
    outfile = "repair_1901_1986.txt"
    with open(outfile, "w") as f:
        f.write(",".join(target_ids))
    print(f"Saved IDs to {outfile}")
    
    # Create partitions for 5 workers
    chunk_size = len(target_ids) // 5 + (1 if len(target_ids) % 5 > 0 else 0)
    for i in range(5):
        chunk = target_ids[i*chunk_size : (i+1)*chunk_size]
        if chunk:
            part_file = f"repair_1901_1986_part{i+1}.txt"
            with open(part_file, "w") as f:
                f.write(",".join(chunk))
            print(f"Created partition {part_file} with {len(chunk)} IDs")

if __name__ == "__main__":
    main()
