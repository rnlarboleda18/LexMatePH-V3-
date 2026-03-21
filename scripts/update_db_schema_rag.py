import psycopg2
import os

def run_rag_migration():
    conn_str = os.environ.get("DB_CONNECTION_STRING") or "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"
    try:
        conn = psycopg2.connect(conn_str)
        conn.autocommit = True # Required for CREATE EXTENSION
        cur = conn.cursor()
        
        print("Running schema update for RAG specific features...")
        
        # 1. Enable Vector Extension
        try:
            print("Enabling vector extension...")
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            print("Vector extension enabled.")
        except Exception as e:
            print(f"Error enabling vector extension: {e}")

        # 2. Add embedding column to supreme_decisions
        # Note: User mentioned 'case_digests' but our table is 'supreme_decisions'. I will use 'supreme_decisions'.
        try:
            print("Adding embedding column...")
            cur.execute("ALTER TABLE supreme_decisions ADD COLUMN IF NOT EXISTS embedding vector(768);")
            print("Embedding column added.")
        except Exception as e:
            print(f"Error adding embedding column: {e}")

        # 3. Create Index
        try:
            print("Creating HNSW index...")
            # Using specific name to check existence or just rely on 'IF NOT EXISTS' equivalent for indexes (Postgres 9.5+ supports IF NOT EXISTS for indexes but standard sql doesn't always)
            # safer to just try create and catch error if exists, or query system cat.
            # Simpler: CREATE INDEX IF NOT EXISTS supreme_decisions_embedding_idx ON supreme_decisions USING hnsw (embedding vector_cosine_ops);
            cur.execute("CREATE INDEX IF NOT EXISTS supreme_decisions_embedding_idx ON supreme_decisions USING hnsw (embedding vector_cosine_ops);")
            print("HNSW index created.")
        except Exception as e:
            print(f"Error creating index: {e}")
        
        cur.close()
        conn.close()
        print("RAG Schema update complete.")

    except Exception as e:
        print(f"Connection Error: {e}")

if __name__ == "__main__":
    run_rag_migration()
