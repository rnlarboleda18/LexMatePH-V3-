import psycopg2

DB_CONNECTION_STRING = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"

def investigate_failed():
    # Read the not_updated list
    with open("audit_not_updated.txt", "r") as f:
        failed_ids = [int(line.strip()) for line in f if line.strip()]
    
    print(f"Investigating {len(failed_ids)} failed cases...\n")
    
    # Check which batches they belong to
    batch_distribution = {}
    for i in range(1, 21):
        batch_file = f"batch_facts_{i}.txt"
        try:
            with open(batch_file, 'r') as f:
                batch_ids = set(int(line.strip()) for line in f if line.strip())
                failed_in_batch = len(set(failed_ids) & batch_ids)
                total_in_batch = len(batch_ids)
                if failed_in_batch > 0:
                    batch_distribution[i] = {
                        'failed': failed_in_batch,
                        'total': total_in_batch,
                        'pct': (failed_in_batch/total_in_batch)*100
                    }
        except FileNotFoundError:
            pass
    
    print("Batch Distribution of Failed Cases:")
    print("-" * 60)
    for batch_num, stats in sorted(batch_distribution.items()):
        print(f"Batch {batch_num:2d}: {stats['failed']:4d}/{stats['total']:4d} failed ({stats['pct']:5.1f}%)")
    
    # Sample some failed cases to check characteristics
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()
    
    sample_ids = failed_ids[:10]
    print(f"\nSample of Failed Cases (checking for patterns):")
    print("-" * 60)
    
    for case_id in sample_ids:
        cur.execute("""
            SELECT id, case_number, 
                   LENGTH(full_text_md) as text_length,
                   digest_facts IS NOT NULL as has_facts
            FROM sc_decided_cases 
            WHERE id = %s
        """, (case_id,))
        
        row = cur.fetchone()
        if row:
            print(f"Case {row[0]:6d}: {row[1]:20s} | Text: {row[2]:7d} chars | Has Facts: {row[3]}")
    
    conn.close()

if __name__ == "__main__":
    investigate_failed()
