import psycopg2
import re

# Hardcoded for reliability in this session
POSTGRES_CONNECTION_STRING = "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

def extract_years():
    print("Connecting to PostgreSQL...")
    try:
        conn = psycopg2.connect(POSTGRES_CONNECTION_STRING)
        cur = conn.cursor()
        
        # 1. Process Questions
        print("Processing Questions...")
        cur.execute("SELECT id, text, source_label FROM questions")
        questions = cur.fetchall()
        
        updated_count = 0
        for q in questions:
            q_id, text, label = q
            if not text: continue
            
            # Regex to find years at the end
            # Matches: (19xx or 20xx) followed by optional space/comma, repeated, at end of string
            # Handles optional parentheses wrapping the whole thing
            match = re.search(r'[\(\s]((?:(?:19|20)\d{2}(?:[\s,]+)?)+)[\)]?[\.\s]*$', text)
            
            if match:
                years_str = match.group(1)
                # Verify it looks like a year list
                if re.match(r'^(?:(?:19|20)\d{2}(?:[\s,]+)?)+$', years_str.strip()):
                    # Clean up years string (remove extra spaces/commas)
                    years = re.findall(r'(19|20)\d{2}', years_str)
                    clean_years = ", ".join(sorted(list(set(years)))) # Unique and sorted
                    
                    # Update Label
                    new_label = label
                    if not new_label or new_label == 'QuAMTO':
                        new_label = clean_years
                    else:
                        new_label = f"{new_label}, {clean_years}"
                    
                    # Update Text (Remove the match)
                    # We remove the whole match group 0, which includes the leading space/paren
                    new_text = text[:match.start()].strip()
                    # Remove trailing punctuation that might be left behind (like a comma before the years)
                    new_text = re.sub(r'[\,\s]+$', '', new_text)
                    # Ensure it ends with a period or question mark if it looked like a sentence? 
                    # Actually, usually these are just appended. Let's just strip.
                    
                    # Execute Update
                    cur.execute(
                        "UPDATE questions SET text = %s, source_label = %s WHERE id = %s",
                        (new_text, new_label, q_id)
                    )
                    updated_count += 1
                    if updated_count % 100 == 0:
                        print(f"Updated {updated_count} questions...")

        print(f"Total Questions Updated: {updated_count}")
        
        # 2. Process Answers
        print("Processing Answers...")
        
        # Cache Question Labels first to avoid N+1 queries
        print("Caching Question Labels...")
        cur.execute("SELECT id, source_label FROM questions")
        question_labels = {row[0]: row[1] for row in cur.fetchall()}
        print(f"Cached {len(question_labels)} question labels.")
        
        cur.execute("SELECT id, question_id, text FROM answers")
        answers = cur.fetchall()
        
        updated_answers_count = 0
        for a in answers:
            a_id, q_id, text = a
            if not text: continue
            
            match = re.search(r'[\(\s]((?:(?:19|20)\d{2}(?:[\s,]+)?)+)[\)]?[\.\s]*$', text)
            
            if match:
                years_str = match.group(1)
                if re.match(r'^(?:(?:19|20)\d{2}(?:[\s,]+)?)+$', years_str.strip()):
                    years = re.findall(r'(19|20)\d{2}', years_str)
                    clean_years = ", ".join(sorted(list(set(years))))
                    
                    # Get current label from cache
                    if q_id and q_id in question_labels:
                        current_label = question_labels[q_id]
                        
                        # Update Label
                        new_label = current_label
                        if not new_label or new_label == 'QuAMTO':
                            new_label = clean_years
                        else:
                            # Avoid duplicates in label
                            existing_years = re.findall(r'(19|20)\d{2}', new_label)
                            all_years = set(existing_years + years)
                            new_label = ", ".join(sorted(list(all_years)))
                        
                        # Update Question Label in DB
                        cur.execute("UPDATE questions SET source_label = %s WHERE id = %s", (new_label, q_id))
                        # Update Cache
                        question_labels[q_id] = new_label
                        
                        # Update Answer Text
                        new_text = text[:match.start()].strip()
                        new_text = re.sub(r'[\,\s]+$', '', new_text)
                        
                        cur.execute("UPDATE answers SET text = %s WHERE id = %s", (new_text, a_id))
                        
                        updated_answers_count += 1
                        if updated_answers_count % 100 == 0:
                            conn.commit() # Commit incrementally
                            print(f"Updated {updated_answers_count} answers...")

        print(f"Total Answers Updated: {updated_answers_count}")

        conn.commit()
        cur.close()
        conn.close()
        print("Extraction Complete.")
        
    except Exception as e:
        print(f"Error: {e}")
        if conn: conn.rollback()

if __name__ == "__main__":
    extract_years()
