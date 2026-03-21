import sqlite3
import re

def fix_merged_answers():
    db_path = 'data/questions.db'
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Get all questions
    cur.execute("SELECT id, text FROM questions")
    questions = cur.fetchall()
    
    fixed_count = 0
    
    print(f"Scanning {len(questions)} questions...")

    for q_id, text in questions:
        # Regex to find "A:" or "A :" or "(20xx) BAR) A:" etc.
        # We look for "A:" that is likely the start of the answer.
        # The pattern in the example was "(2012) BAR) A: YES"
        
        # Simple split first: Look for " A: " or "\nA:" or ") A:"
        # We want to be careful not to split on "A:" appearing in normal text if possible,
        # but " A: " is a strong signal.
        
        # Pattern: 
        # 1. Newline followed by A:
        # 2. Space followed by A:
        # 3. Closing parenthesis followed by A: (common in this dataset)
        
        match = re.search(r'(?:\n|\s|\))A:\s*', text)
        
        if match:
            split_index = match.start()
            # If it's a parenthesis, we want to keep the parenthesis in the question
            if text[split_index] == ')':
                split_index += 1
            
            question_text = text[:split_index].strip()
            answer_text = text[match.end():].strip() # match.end() skips the "A:" part
            
            if len(answer_text) > 0:
                # Update question text
                cur.execute("UPDATE questions SET text = ? WHERE id = ?", (question_text, q_id))
                
                # Check if answer exists
                cur.execute("SELECT id FROM answers WHERE question_id = ?", (q_id,))
                existing_answer = cur.fetchone()
                
                if existing_answer:
                    # Update existing answer
                    cur.execute("UPDATE answers SET text = ? WHERE id = ?", (answer_text, existing_answer[0]))
                else:
                    # Insert new answer
                    cur.execute("INSERT INTO answers (question_id, text, institution, source_url) VALUES (?, ?, ?, ?)", 
                                (q_id, answer_text, 'Bar Exam', ''))
                
                fixed_count += 1
                if fixed_count % 100 == 0:
                    print(f"Fixed {fixed_count} questions...")

    conn.commit()
    conn.close()
    print(f"Finished. Fixed {fixed_count} merged answers.")

if __name__ == "__main__":
    fix_merged_answers()
