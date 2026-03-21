import pandas as pd
import sqlite3
import os

INPUT_FILE = 'data/Doctrinal Cases_Merged.xlsx'
DB_FILE = 'api/questions.db'

def ingest_doctrinal_cases():
    if not os.path.exists(INPUT_FILE):
        print(f"Input file not found: {INPUT_FILE}")
        return

    print(f"Loading {INPUT_FILE}...")
    xl = pd.ExcelFile(INPUT_FILE)
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create table
    print("Creating table 'doctrinal_cases'...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS doctrinal_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            "Subject" TEXT,
            "Case Title" TEXT,
            "Year" INTEGER,
            "Key Topic" TEXT,
            "Doctrine / Ruling" TEXT,
            "Digest" TEXT,
            "source_label" TEXT
        )
    ''')
    
    # Clear existing data to avoid duplicates (optional, but good for re-runs)
    cursor.execute("DELETE FROM doctrinal_cases")
    
    total_ingested = 0
    
    for sheet_name in xl.sheet_names:
        print(f"Ingesting sheet: {sheet_name}")
        df = xl.parse(sheet_name)
        
        # Normalize columns
        # Expected: No., Subject, Case Title, Year, Key Topic, Doctrine / Ruling, Digest
        
        for _, row in df.iterrows():
            subject = row['Subject']
            case_title = row['Case Title']
            year = row['Year']
            topic = row['Key Topic']
            doctrine = row['Doctrine / Ruling']
            digest = row.get('Digest', '') # Might be NaN if generation failed
            
            # Determine source_label
            source_label = row.get('source_label')
            if pd.isna(source_label):
                source_label = None
            
            cursor.execute('''
                INSERT INTO doctrinal_cases ("Subject", "Case Title", "Year", "Key Topic", "Doctrine / Ruling", "Digest", "source_label")
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (subject, case_title, year, topic, doctrine, digest, source_label))
            
            total_ingested += 1
            
    conn.commit()
    conn.close()
    print(f"Successfully ingested {total_ingested} cases into {DB_FILE}")

if __name__ == "__main__":
    ingest_doctrinal_cases()
