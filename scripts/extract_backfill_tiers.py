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

def extract_backfill_tiers():
    conn = get_db_connection()
    cur = conn.cursor()

    # 1. Significance Backfill (Significance is NULL or Unknown)
    query_sig = """
        SELECT id FROM sc_decided_cases 
        WHERE ai_model IS NOT NULL 
          AND (digest_significance IS NULL OR digest_significance = '' OR digest_significance = 'Unknown')
        ORDER BY id ASC
    """
    cur.execute(query_sig)
    sig_ids = [str(row[0]) for row in cur.fetchall()]
    with open('backfill_significance_ids.txt', 'w') as f:
        f.write('\n'.join(sig_ids))
    print(f"Exported {len(sig_ids)} IDs to backfill_significance_ids.txt")

    # 2. General Backfill (Any other field missing, ignoring significance status for this group)
    # The user asked: "All other cases where any of the fields are empty (except Significance)"
    # This implies we exclude cases captured in the first group, OR we just check the other fields.
    # To be precise: Cases where SIGNIFICANCE is OK, but OTHER fields are MISSING.
    query_gen = """
        SELECT id FROM sc_decided_cases 
        WHERE ai_model IS NOT NULL 
          AND (digest_significance IS NOT NULL AND digest_significance != '' AND digest_significance != 'Unknown')
          AND (
              digest_facts IS NULL OR digest_facts = '' OR
              digest_issues IS NULL OR digest_issues = '' OR
              digest_ruling IS NULL OR digest_ruling = '' OR
              digest_ratio IS NULL OR digest_ratio = '' OR
              keywords IS NULL OR 
              legal_concepts IS NULL OR 
              flashcards IS NULL OR 
              spoken_script IS NULL OR spoken_script = ''
          )
        ORDER BY id ASC
    """
    cur.execute(query_gen)
    gen_ids = [str(row[0]) for row in cur.fetchall()]
    with open('backfill_general_ids.txt', 'w') as f:
        f.write('\n'.join(gen_ids))
    print(f"Exported {len(gen_ids)} IDs to backfill_general_ids.txt")

    conn.close()

if __name__ == "__main__":
    extract_backfill_tiers()
