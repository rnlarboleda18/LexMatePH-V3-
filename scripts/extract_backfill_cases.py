import psycopg2
import os
import json

def get_db_connection():
    """Get database connection"""
    db_connection_string = "postgresql://postgres:password@localhost:5432/sc_decisions"
    try:
        with open('api/local.settings.json', 'r') as f:
            settings = json.load(f)
            db_connection_string = settings['Values']['DB_CONNECTION_STRING']
    except:
        pass
    return psycopg2.connect(db_connection_string)

def load_ghost_fleet_ids():
    """Load IDs from combined ghost fleet to exclude"""
    try:
        with open('ghost_fleet_combined.txt', 'r', encoding='utf-8-sig') as f:
            return set(int(line.strip()) for line in f if line.strip())
    except:
        return set()

# Get data
ghost_ids = load_ghost_fleet_ids()
conn = get_db_connection()
cur = conn.cursor()

# Exclusion for ghost fleet
exclusion_clause = "AND id != ALL(%s)" if ghost_ids else ""
exclusion_param = (list(ghost_ids),) if ghost_ids else ()

# Get cases missing flashcards OR spoken_script (union)
query = f"""
    SELECT DISTINCT id 
    FROM sc_decided_cases 
    WHERE ai_model IS NOT NULL 
    AND full_text_md IS NOT NULL AND full_text_md != ''
    AND (
        flashcards IS NULL OR flashcards::text = '[]' OR flashcards::text = '{{}}'
        OR spoken_script IS NULL OR spoken_script::text = '[]' OR spoken_script::text = '{{}}'
    )
    {exclusion_clause}
    ORDER BY id
"""
cur.execute(query, exclusion_param)
backfill_ids = [row[0] for row in cur.fetchall()]

print(f"Cases needing backfill: {len(backfill_ids):,}")
print(f"Excluded (in ghost fleet): {len(ghost_ids):,}")
print(f"\nWriting to backfill_optional_fields.txt...")

# Write to file
with open('backfill_optional_fields.txt', 'w', encoding='utf-8') as f:
    for case_id in backfill_ids:
        f.write(f"{case_id}\n")

print(f"✓ Wrote {len(backfill_ids):,} case IDs")

# Distribution for 30 workers
chunk_size = len(backfill_ids) // 30
remainder = len(backfill_ids) % 30

chunks = []
start = 0
for i in range(30):
    size = chunk_size + (1 if i < remainder else 0)
    chunks.append(backfill_ids[start:start + size])
    start += size

# Write worker files
for i, chunk in enumerate(chunks, 1):
    filename = f'backfill_worker_{i}.txt'
    with open(filename, 'w', encoding='utf-8') as f:
        for case_id in chunk:
            f.write(f"{case_id}\n")
    print(f"Created {filename}: {len(chunk)} IDs")

print(f"\nTotal distributed: {sum(len(c) for c in chunks):,} cases across 30 workers")

conn.close()
