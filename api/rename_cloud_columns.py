import psycopg2

# Cloud connection string
CLOUD_DB = "postgresql://bar_admin:RABpass021819!@bar-db-eu-west.postgres.database.azure.com:5432/postgres?sslmode=require"

def migrate_schema():
    print("Connecting to CLOUD DB for migration...")
    conn = psycopg2.connect(CLOUD_DB)
    cur = conn.cursor()

    try:
        # Renaming columns to match ROC structure
        renames = {
            "book": "part_num",
            "book_label": "part_title",
            "title_num": "rule_num",
            "title_label": "rule_title_full",
            "article_num": "rule_section_label",
            "article_title": "section_title",
            "content_md": "section_content",
            "chapter_label": "group_1_title",
            "section_label": "group_2_title",
            "chapter_num": "group_1_num",
            "chapter": "group_context"
        }

        for old_col, new_col in renames.items():
            print(f"Renaming {old_col} to {new_col}...")
             # Check if old column exists first
            cur.execute(f"""
                SELECT COUNT(*) FROM information_schema.columns 
                WHERE table_name = 'roc_codal' AND column_name = '{old_col}'
            """)
            if cur.fetchone()[0] > 0:
                cur.execute(f"ALTER TABLE roc_codal RENAME COLUMN {old_col} TO {new_col}")
            else:
                print(f"Warning: Column {old_col} not found or already renamed.")

        # Adding new columns if necessary
        # 1. source_ref (for things like (1a), (n))
        cur.execute("""
            SELECT COUNT(*) FROM information_schema.columns 
            WHERE table_name = 'roc_codal' AND column_name = 'source_ref'
        """)
        if cur.fetchone()[0] == 0:
            print("Adding column source_ref...")
            cur.execute("ALTER TABLE roc_codal ADD COLUMN source_ref TEXT")

        conn.commit()
        print("Schema migration completed successfully.")

    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_schema()
