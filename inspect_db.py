import os
import sqlite3

def list_all_tables():
    for root, dirs, files in os.walk(r'C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2'):
        for file in files:
            if file.endswith('.db'):
                db_path = os.path.join(root, file)
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                    tables = cursor.fetchall()
                    if tables:
                        print(f'\nTables in {db_path}:')
                        for table in tables:
                            print(f'  - {table[0]}')
                except Exception as e:
                    pass

if __name__ == "__main__":
    list_all_tables()
