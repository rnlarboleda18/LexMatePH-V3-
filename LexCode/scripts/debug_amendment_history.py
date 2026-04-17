import psycopg2, json, sys
from pathlib import Path

def debug():
    settings = Path('api/local.settings.json')
    cs = json.loads(settings.read_text()).get('Values', {}).get('DB_CONNECTION_STRING')
    conn = psycopg2.connect(cs)
    cur = conn.cursor()

    # Get article_versions columns
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'article_versions'")
    cols = [c[0] for c in cur.fetchall()]
    print(f"article_versions columns: {cols}")

    # Get rpc_codal columns
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'rpc_codal'")
    cols_codal = [c[0] for c in cur.fetchall()]
    print(f"rpc_codal columns: {cols_codal}")

    # Search for Art 329
    cur.execute("SELECT * FROM rpc_codal WHERE article_num='329'")
    codal = cur.fetchone()
    print(f"\nArt 329 in rpc_codal: {codal}")

    if codal:
        # Assuming first column is the ID if it's not named 'id'
        codal_id = codal[0]
        # Dynamically build query for versions
        v_cols = ["version_name", "enacted_date"]
        # Find which column relates to the codal ID
        fk_col = next((c for c in cols if "codal" in c or "article" in c), None)
        print(f"Likely FK column in article_versions: {fk_col}")
        
        if fk_col:
            q = f"SELECT version_name, enacted_date, content_md FROM article_versions WHERE {fk_col} = %s"
            cur.execute(q, (codal_id,))
            versions = cur.fetchall()
            print(f"\nVersions found ({len(versions)}):")
            for v in versions:
                print(v[:2]) # print name and date
        else:
            print("Could not find FK column for article_versions")

    cur.close()
    conn.close()

if __name__ == "__main__":
    debug()
