import sqlite3

def add_source_column():
    db_path = 'data/questions.db'
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    try:
        # Check if column exists
        cur.execute("PRAGMA table_info(questions)")
        columns = [info[1] for info in cur.fetchall()]
        
        if 'source_label' not in columns:
            print("Adding source_label column...")
            cur.execute("ALTER TABLE questions ADD COLUMN source_label TEXT DEFAULT 'QuAMTO'")
            cur.execute("UPDATE questions SET source_label = 'QuAMTO'")
            conn.commit()
            print("Column added and populated.")
        else:
            print("Column source_label already exists. Updating values...")
            cur.execute("UPDATE questions SET source_label = 'QuAMTO'")
            conn.commit()
            print("Values updated.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_source_column()
