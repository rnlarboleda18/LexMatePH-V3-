import os
import re
import psycopg2
from psycopg2.extras import execute_values
import json

# DB Config pointing to Azure Cloud DB
DB_CONN = "postgresql://bar_admin:RABpass021819!@lexmateph-ea-db.postgres.database.azure.com:5432/lexmateph-ea-db?sslmode=require"

# Mapping filenames to DB subjects
SUBJECT_MAP = {
    "Quamto 2023 Civil Law_AI.md": "Civil Law",
    "5_Political_Law_QUAMTO_AI.md": "Political Law",
    "2_Criminal_Law_QUAMTO_AI.md": "Criminal Law",
    "3_Labor_Law_QUAMTO_AI.md": "Labor Law",
    "4_Legal_Ethics_QUAMTO_AI.md": "Legal Ethics",
    "7_Remedial_Law_QUAMTOL_AI.md": "Remedial Law",
    "6_Commercial_Law_QQUAMTOL_AI.md": "Commercial Law",
    "8_Taxation_Law_QUAMTO_AI.md": "Taxation Law"
}

def parse_md_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Split content by "Question (" header OR "Q#:" question marker
    units = re.split(r'\n(?=Question\s*\(|Q\d+[a-z]?:)', content)
    qa_pairs = []
    
    current_context_year = 0
    last_major_id = None
    last_subject = None
    
    for unit in units:
        unit = unit.strip()
        if not unit or "AI Extracted Q&A" in unit:
            continue
            
        # 1. Update context year if this unit is a header
        header_match = re.search(r"Question\s*\(.*?\D?(\d{4}).*?\)", unit, re.IGNORECASE)
        if header_match:
            current_context_year = int(header_match.group(1))
            
        # 2. Extract Marker (e.g., Q1, Q4a)
        marker_match = re.search(r"^Q(\d+)([a-z])?:", unit, re.IGNORECASE)
        has_answer = "Suggested Answer" in unit
        
        if marker_match and has_answer:
            major_id = marker_match.group(1)
            minor_id = marker_match.group(2) # 'a', 'b', etc.
            
            # Extract Year
            embedded_year_match = re.search(r"\(\D?(\d{4}).*?BAR\)", unit, re.IGNORECASE)
            year = current_context_year
            if embedded_year_match:
                year = int(embedded_year_match.group(1))
            
            # Split at Suggested Answer
            parts = re.split(r'\n\s*Suggested Answer\s*\n', unit, maxsplit=1, flags=re.IGNORECASE)
            if len(parts) == 2:
                q_text = parts[0].strip()
                # Remove ONLY the Q1: part, keep the rest (like (a) if present)
                q_text = re.sub(r"^Q\d+[a-z]?:\s*", "", q_text, flags=re.IGNORECASE).strip()
                
                a_text = parts[1].strip()
                a_text = re.sub(r"^A\d+[a-z]?:\s*", "", a_text, flags=re.IGNORECASE).strip()
                
                # Check if this belongs to the previous parent (same major_id and year)
                if last_major_id == major_id and qa_pairs and qa_pairs[-1]["year"] == year:
                    # APPEND to existing record
                    qa_pairs[-1]["question"] += f"\n\n{q_text}"
                    qa_pairs[-1]["answer"] += f"\n\n{a_text}"
                else:
                    # New Parent
                    qa_pairs.append({
                        "year": year,
                        "question": q_text,
                        "answer": a_text
                    })
                    last_major_id = major_id
                
    return qa_pairs

def ingest_data():
    md_dir = r"C:\Users\rnlar\.gemini\antigravity\scratch\LexMatePH v3\pdf quamto\ai_md"
    
    try:
        conn = psycopg2.connect(DB_CONN)
        cur = conn.cursor()
        
        # 1. Truncate existing data
        print("Clearing existing Bar Question and Answer entries...")
        cur.execute("TRUNCATE TABLE answers, questions RESTART IDENTITY CASCADE")
        
        # 2. Process files
        total_q = 0
        for filename, subject in SUBJECT_MAP.items():
            file_path = os.path.join(md_dir, filename)
            if not os.path.exists(file_path):
                print(f"File not found: {filename}. Skipping.")
                continue
                
            print(f"Parsing {filename} for subject: {subject}...")
            pairs = parse_md_file(file_path)
            print(f"  -> Extracted {len(pairs)} questions.")
            
            for p in pairs:
                # Insert Question
                cur.execute(
                    "INSERT INTO questions (year, subject, text, source_url, source_label) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                    (p["year"], subject, p["question"], "AI Extraction", "QuAMTO")
                )
                q_id = cur.fetchone()[0]
                
                # Insert Answer
                cur.execute(
                    "INSERT INTO answers (question_id, text, source_url) VALUES (%s, %s, %s)",
                    (q_id, p["answer"], "AI Extraction")
                )
                total_q += 1
        
        conn.commit()
        print(f"\nSUCCESS: Ingested total of {total_q} questions into PostgreSQL.")
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"CRITICAL ERROR during ingestion: {e}")
        if 'conn' in locals():
            conn.rollback()

if __name__ == "__main__":
    ingest_data()
