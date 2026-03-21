import sqlite3
import os
from docx import Document

# Configuration
DOCX_FILENAME = "2024 Labor Law Bar Questions.docx" # REPLACE THIS with your actual filename
DB_PATH = "data/questions.db"
TARGET_YEAR = 2024
TARGET_SUBJECT = "Labor Law"
SOURCE_LABEL = "2024 Bar Exams"

def ingest_docx():
    docx_path = os.path.join("data", DOCX_FILENAME)
    
    if not os.path.exists(docx_path):
        print(f"Error: File not found at {docx_path}")
        print("Please place your DOCX file in the 'data' folder and update DOCX_FILENAME in this script.")
        return

    print(f"Reading {docx_path}...")
    doc = Document(docx_path)
    
    questions = []
    current_q = None
    
    # State machine: 'NONE', 'QUESTION', 'ANSWER'
    state = 'NONE'
    
    def get_para_text(para):
        """Extract text from paragraph, preserving manual line breaks using XML."""
        text = ""
        namespace = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
        
        # Iterate over all children of the paragraph element
        for child in para._element:
            # Check for Run
            if child.tag == f'{namespace}r':
                for grandchild in child:
                    if grandchild.tag == f'{namespace}t':
                        text += grandchild.text or ""
                    elif grandchild.tag == f'{namespace}br':
                        text += "\n\n"
                    elif grandchild.tag == f'{namespace}cr':
                        text += "\n\n"
            # Check for direct breaks (rare but possible)
            elif child.tag == f'{namespace}br':
                text += "\n\n"
                
        return text.strip()

    for para in doc.paragraphs:
        # Use the custom text extractor
        text = get_para_text(para)
        if not text: continue
        
        # Check for markers
        if text.upper().startswith("Q:"):
            # Save previous question if exists
            if current_q:
                questions.append(current_q)
            
            # Start new question
            state = 'QUESTION'
            # Remove "Q:" prefix
            clean_text = text[2:].strip()
            current_q = {
                "question": clean_text,
                "answer": "",
                "year": TARGET_YEAR,
                "subject": TARGET_SUBJECT
            }
            
        elif text.upper().startswith("A:"):
            if state == 'NONE':
                print(f"Warning: Found 'A:' without preceding 'Q:'. Skipping: {text[:50]}...")
                continue
                
            state = 'ANSWER'
            # Remove "A:" prefix
            clean_text = text[2:].strip()
            if current_q:
                current_q["answer"] = clean_text
                
        else:
            # Continuation text
            if state == 'QUESTION' and current_q:
                current_q["question"] += "\n\n" + text
            elif state == 'ANSWER' and current_q:
                current_q["answer"] += "\n\n" + text
    
    # Append the last question
    if current_q:
        questions.append(current_q)
        
    print(f"Found {len(questions)} questions.")
    
    # Insert into Database
    if not questions:
        print("No questions found. Check your file formatting (ensure 'Q:' and 'A:' markers are used).")
        return

    print(f"Inserting into {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    inserted_count = 0
    for q in questions:
        try:
            # 1. Insert Question
            cur.execute("""
                INSERT INTO questions (year, subject, text, source_label)
                VALUES (?, ?, ?, ?)
            """, (q['year'], q['subject'], q['question'], SOURCE_LABEL))
            
            q_id = cur.lastrowid
            
            # 2. Insert Answer
            if q['answer']:
                cur.execute("""
                    INSERT INTO answers (question_id, institution, text)
                    VALUES (?, ?, ?)
                """, (q_id, 'Suggested Answer', q['answer']))
            
            inserted_count += 1
            
        except Exception as e:
            print(f"Error inserting question: {e}")
            
    conn.commit()
    conn.close()
    print(f"Successfully inserted {inserted_count} questions.")

if __name__ == "__main__":
    ingest_docx()
