import psycopg2
import os
import json
import logging
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("fix_ponentes.log"),
        logging.StreamHandler()
    ]
)

def get_db_connection():
    """Get database connection"""
    db_connection_string = "postgresql://postgres:password@localhost:5432/sc_decisions"
    try:
        with open('api/local.settings.json', 'r') as f:
            settings = json.load(f)
            db_connection_string = settings['Values']['DB_CONNECTION_STRING']
    except:
        pass
    return psycopg2.connect(db_connection_string)

def normalize_ponente(ponente):
    """
    Normalize ponente name to standard format: "LASTNAME, J.:"
    Examples:
        "Antonio T. Carpio" -> "CARPIO, J.:"
        "carpio, j." -> "CARPIO, J.:"
        "CARPIO, J" -> "CARPIO, J.:"
        "Carpio" -> "CARPIO, J.:"
    """
    if not ponente or not isinstance(ponente, str):
        return None
    
    # Clean up the input
    ponente = ponente.strip()
    if not ponente:
        return None
    
    # Already in correct format (uppercase with J.:)
    if ponente.isupper() and ', J.:' in ponente:
        return ponente
    
    # Extract the lastname
    lastname = None
    
    # Pattern 1: "LASTNAME, J." or "LASTNAME, J.:" or "Lastname, J."
    if ', J' in ponente.upper():
        lastname = ponente.split(',')[0].strip()
    
    # Pattern 2: "Firstname Middlename Lastname" (full name format)
    elif ' ' in ponente and ',' not in ponente:
        # Take the last word as lastname
        parts = ponente.split()
        lastname = parts[-1]
    
    # Pattern 3: Just lastname alone
    else:
        lastname = ponente
    
    if lastname:
        # Remove any trailing periods or colons
        lastname = lastname.rstrip('.:').strip()
        # Convert to uppercase and add standard suffix
        return f"{lastname.upper()}, J.:"
    
    return None

def fix_existing_ponentes():
    conn = get_db_connection()
    cur = conn.cursor()
    
    print("Fetching cases with ponente...")
    cur.execute("SELECT id, ponente FROM sc_decided_cases WHERE ponente IS NOT NULL AND ponente != ''")
    cases = cur.fetchall()
    
    print(f"Found {len(cases)} cases to check.")
    
    updated_count = 0
    skipped_count = 0
    error_count = 0
    
    batch_updates = []
    BATCH_SIZE = 1000
    
    for case_id, ponente in tqdm(cases):
        try:
            normalized = normalize_ponente(ponente)
            
            if normalized and normalized != ponente:
                batch_updates.append((normalized, case_id))
                updated_count += 1
            else:
                skipped_count += 1
                
            if len(batch_updates) >= BATCH_SIZE:
                psycopg2.extras.execute_batch(
                    cur,
                    "UPDATE sc_decided_cases SET ponente = %s WHERE id = %s",
                    batch_updates
                )
                conn.commit()
                batch_updates = []
                
        except Exception as e:
            logging.error(f"Error processing case {case_id}: {e}")
            error_count += 1
            
    # Process remaining
    if batch_updates:
        psycopg2.extras.execute_batch(
            cur,
            "UPDATE sc_decided_cases SET ponente = %s WHERE id = %s",
            batch_updates
        )
        conn.commit()
    
    print("\n" + "="*50)
    print("PONENTE NORMALIZATION COMPLETE")
    print("="*50)
    print(f"Total Cases Checked: {len(cases)}")
    print(f"Updated:             {updated_count}")
    print(f"Already Correct/Skipped: {skipped_count}")
    print(f"Errors:              {error_count}")
    
    conn.close()

if __name__ == "__main__":
    import psycopg2.extras
    fix_existing_ponentes()
