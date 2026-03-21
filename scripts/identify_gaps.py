import psycopg2

DB_CONNECTION_STRING = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"

def get_ids():
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()

    # 1. Missing Ratio
    cur.execute("SELECT id FROM sc_decided_cases WHERE digest_ratio IS NULL OR digest_ratio = ''")
    ratio_ids = [str(r[0]) for r in cur.fetchall()]
    
    # 2. Missing Significance
    cur.execute("SELECT id FROM sc_decided_cases WHERE digest_significance IS NULL OR digest_significance = ''")
    sig_ids = [str(r[0]) for r in cur.fetchall()]
    
    # 3. Missing Metadata (Case Number)
    cur.execute("SELECT id FROM sc_decided_cases WHERE case_number IS NULL OR case_number = ''")
    meta_ids = [str(r[0]) for r in cur.fetchall()]

    conn.close()
    
    print(f"MISSING_RATIO_IDS={','.join(ratio_ids)}")
    print(f"MISSING_SIG_IDS={','.join(sig_ids)}")
    print(f"MISSING_META_IDS={','.join(meta_ids)}")

if __name__ == "__main__":
    get_ids()
