import os
import sqlite3
import psycopg2
import psycopg2.extras
from psycopg2 import sql

# Configuration
SQLITE_DB_PATH = 'data/questions.db'
# Hardcoded for reliability in this session
POSTGRES_CONNECTION_STRING = "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

def migrate():
    print(f"Connecting to SQLite: {SQLITE_DB_PATH}")
    sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    print("Connecting to PostgreSQL...")
    try:
        pg_conn = psycopg2.connect(POSTGRES_CONNECTION_STRING)
        pg_cur = pg_conn.cursor()
    except Exception as e:
        print(f"Failed to connect to PostgreSQL: {e}")
        return

    # 1. Migrate Questions
    print("Migrating Questions...")
    
    # Drop and Recreate to ensure clean state
    pg_cur.execute("DROP TABLE IF EXISTS questions CASCADE;")
    pg_cur.execute("""
        CREATE TABLE questions (
            id SERIAL PRIMARY KEY,
            year INTEGER NOT NULL,
            subject TEXT NOT NULL,
            text TEXT NOT NULL,
            source_url TEXT,
            source_label TEXT DEFAULT 'QuAMTO'
        );
    """)
    
    # Fetch from SQLite
    sqlite_cur.execute("PRAGMA table_info(questions)")
    columns = [row['name'] for row in sqlite_cur.fetchall()]
    print(f"SQLite columns: {columns}")
    
    cols_to_select = ['year', 'subject', 'text']
    if 'source_url' in columns: cols_to_select.append('source_url')
    if 'source_label' in columns: cols_to_select.append('source_label')

    query = f"SELECT {', '.join(cols_to_select)} FROM questions"
    sqlite_cur.execute(query)
    questions = sqlite_cur.fetchall()
    
    # Batch insert using execute_batch
    print(f"Found {len(questions)} questions. Inserting in batches...")
    
    placeholders = ', '.join(['%s'] * len(cols_to_select))
    insert_query = f"""
        INSERT INTO questions ({', '.join(cols_to_select)})
        VALUES ({placeholders})
    """
    
    try:
        batch_size = 500
        for i in range(0, len(questions), batch_size):
            chunk = questions[i:i + batch_size]
            psycopg2.extras.execute_batch(pg_cur, insert_query, chunk)
            pg_conn.commit()
            print(f"Inserted {min(i + batch_size, len(questions))}/{len(questions)} questions...")
            
        print(f"Inserted all {len(questions)} questions.")
    except Exception as e:
        print(f"Error in batch insert: {e}")
        pg_conn.rollback()
    
    # 2. Migrate Answers
    sqlite_cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='answers'")
    if sqlite_cur.fetchone():
        print("Migrating Answers Table...")
        pg_cur.execute("DROP TABLE IF EXISTS answers CASCADE;")
        pg_cur.execute("""
            CREATE TABLE answers (
                id SERIAL PRIMARY KEY,
                question_id INTEGER,
                institution TEXT,
                text TEXT,
                source_url TEXT
            );
        """)
        
        sqlite_cur.execute("PRAGMA table_info(answers)")
        columns = [row['name'] for row in sqlite_cur.fetchall()]
        
        cols_to_select = []
        if 'question_id' in columns: cols_to_select.append('question_id')
        if 'institution' in columns: cols_to_select.append('institution')
        if 'text' in columns: cols_to_select.append('text')
        if 'source_url' in columns: cols_to_select.append('source_url')
        
        # Note: 'answer' column in answers table is usually 'text'
        
        query = f"SELECT {', '.join(cols_to_select)} FROM answers"
        sqlite_cur.execute(query)
        answers = sqlite_cur.fetchall()
        
        print(f"Found {len(answers)} answers.")
        
        # Use copy_expert for psycopg2
        import io
        csv_buffer = io.StringIO()
        for a in answers:
            q_id = a['question_id'] if 'question_id' in a.keys() else None
            inst = a['institution'] if 'institution' in a.keys() else None
            txt = a['text'] if 'text' in a.keys() else ""
            src = a['source_url'] if 'source_url' in a.keys() else None
            
            # Simple CSV formatting
            row = [str(q_id) if q_id is not None else '', 
                   inst or '', 
                   txt or '', 
                   src or '']
            # Escape special chars if needed, but for now let's try tab separated
            csv_buffer.write("\t".join([str(x).replace('\t', ' ').replace('\n', '\\n') for x in row]) + "\n")
        
        csv_buffer.seek(0)
        pg_cur.copy_from(csv_buffer, 'answers', columns=('question_id', 'institution', 'text', 'source_url'), null='')

    # 3. Create User Attempts Table
    print("Creating user_attempts table...")
    pg_cur.execute("""
        CREATE TABLE IF NOT EXISTS user_attempts (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            question_id INTEGER,
            answer_text TEXT,
            grade_feedback TEXT,
            score INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    pg_conn.commit()
    print("Migration Complete!")
    
    sqlite_conn.close()
    pg_conn.close()

if __name__ == "__main__":
    migrate()
