import psycopg2
import os
import json

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"

TARGET_TYPES = [
    "Concurring Opinion",
    "Dissenting Opinion",
    "Separate Opinion", 
    "Amended Decision"
]

def process_opinions():
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()
    
    print("--- Processing Opinions ---")
    
    deleted_count = 0
    linked_count = 0
    
    for doc_type in TARGET_TYPES:
        cur.execute("SELECT id, case_number, full_text_md, short_title FROM sc_decided_cases WHERE document_type = %s", (doc_type,))
        rows = cur.fetchall()
        
        for row in rows:
            case_id, case_num, content, title = row
            
            # Find Parent
            parent_id = None
            if case_num:
                cur.execute("""
                    SELECT id, document_type, separate_opinions 
                    FROM sc_decided_cases 
                    WHERE case_number = %s 
                      AND id != %s 
                      AND document_type IN ('Decision', 'Resolution')
                """, (case_num, case_id))
                parents = cur.fetchall()
                if parents:
                    parent = parents[0]
                    parent_id = parent[0]
                    parent_ops = parent[2] or [] # Default to list
                    
            if parent_id:
                # MATCH FOUND: LINK (Append to Parent)
                print(f"LINKING ID {case_id} ({doc_type}) -> Parent {parent_id}...")
                
                # Create opinion object
                new_op = {
                    "type": doc_type,
                    "justice": "Unknown (Linked)", # No extraction here, simplistic
                    "summary": f"Linked from ID {case_id}: {title}. Content snippet: {content[:100]}..."
                }
                
                # Append to parent's JSONB list
                if isinstance(parent_ops, str):
                     try:
                        parent_ops = json.loads(parent_ops)
                     except:
                        parent_ops = []
                
                if not isinstance(parent_ops, list):
                    parent_ops = []
                    
                parent_ops.append(new_op)
                
                # Update Parent
                cur.execute("UPDATE sc_decided_cases SET separate_opinions = %s WHERE id = %s", (json.dumps(parent_ops), parent_id))
                
                # Delete Child
                cur.execute("DELETE FROM sc_decided_cases WHERE id = %s", (case_id,))
                linked_count += 1
                
            else:
                # NO PARENT: DELETE (Orphan)
                print(f"DELETING ORPHAN ID {case_id} ({doc_type}). Case Num: {case_num}...")
                cur.execute("DELETE FROM sc_decided_cases WHERE id = %s", (case_id,))
                deleted_count += 1

    conn.commit()
    conn.close()
    
    print(f"\nSummary: Linked {linked_count}, Deleted {deleted_count}.")

if __name__ == "__main__":
    process_opinions()
