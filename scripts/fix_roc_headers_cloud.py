import psycopg2
from psycopg2.extras import RealDictCursor
import re
import sys

DB_URL = "postgresql://bar_admin:[DB_PASSWORD]@bar-db-eu-west.postgres.database.azure.com:5432/postgres?sslmode=require"

def main():
    commit = "--commit" in sys.argv
    print(f"Connecting to Cloud DB... Mode: {'COMMIT' if commit else 'DRY RUN'}")
    
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur_write = conn.cursor()

    print("Fetching ROC rows...")
    cur.execute("SELECT id, article_num, article_title, content_md FROM roc_codal")
    rows = cur.fetchall()

    fixed_count = 0
    # Matches a period, then any spaces, then any type of dash (–, —, -), then any spaces
    split_pattern = re.compile(r'\.\s*[–—\-]\s*')

    print("\nEvaluating rows for repair...\n" + "=" * 50)
    
    for r in rows:
        title = (r['article_title'] or "").strip()
        content = (r['content_md'] or "").strip()
        
        if not content:
             continue

        # Strategy: Split content at absolute first occurrence of '. –' or similar dash-divider
        parts = split_pattern.split(content, maxsplit=1)
        if len(parts) != 2:
             continue
             
        title_fragment = parts[0].strip()
        body_content = parts[1].strip()

        # Is this a valid title fragment?
        # Typically looks like 'joinder of necessary parties' (Starts with small letter or continues title)
        # OR title matches known stubs ('Non', 'co', 'and')
        is_broken = False
        if title_fragment and title_fragment[0].islower():
             is_broken = True
        elif title in ["Non", "co", "and", "Misjoinder and non"]:
             is_broken = True

        if is_broken:
             # Merge titles
             # Standard formatting: Non + joinder -> Non-joinder if hyphen needed, 
             # but standard spaces generally work safely if the local ingestion omitted them!
             # Let's join with space first.
             new_title = f"{title} {title_fragment}".strip()
             new_content = body_content
             
             fixed_count += 1
             print(f"ID: {r['id']}")
             print(f"  Old Title: {title!r}")
             print(f"  Fragment:  {title_fragment!r}")
             print(f"  -> New:    {new_title!r}")
             
             if commit:
                  cur_write.execute("""
                      UPDATE roc_codal
                      SET article_title = %s, content_md = %s, updated_at = NOW()
                      WHERE id = %s
                  """, (new_title, new_content, r['id']))

    print("=" * 50)
    if commit:
         conn.commit()
         print(f"🎉 Successfully repaired {fixed_count} rows in Cloud!")
    else:
         print(f"🔍 Dry-run matched {fixed_count} rows across ROC layout bounds setup. Run with `--commit` to apply.")

    cur.close()
    cur_write.close()
    conn.close()

if __name__ == "__main__":
    main()
