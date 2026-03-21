import psycopg2
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

conn=psycopg2.connect('postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local')
cur=conn.cursor()

# Target titles with the Mojibake starter marks
cur.execute("SELECT id, short_title FROM sc_decided_cases WHERE short_title LIKE '%Ã%' OR short_title LIKE '%Â%' OR short_title LIKE '%â%'")
rows = cur.fetchall()

logging.info(f"Checking {len(rows)} potential mojibake cases...")

updated_count = 0
error_count = 0
skipped_count = 0

for cid, title in rows:
    try:
        # Attempt to reverse the mojibake:
        # 1. Encode to latin1 -> gets the original bytes (if it really was just decoded as latin1)
        raw_bytes = title.encode('latin1')
        
        # 2. Decode as utf-8 -> interprets those bytes correctly
        fixed_title = raw_bytes.decode('utf-8')
        
        if fixed_title != title:
            # We found a fix!
            cur.execute("UPDATE sc_decided_cases SET short_title = %s, updated_at = NOW() WHERE id = %s", (fixed_title, cid))
            logging.info(f"Fixed {cid}: '{title}' -> '{fixed_title}'")
            updated_count += 1
        else:
            skipped_count += 1
            
    except UnicodeEncodeError:
        # Contains characters not in Latin-1 (e.g. real curly quotes, em-dashes, etc. that are valid)
        # This implies it might NOT be simple mojibake, or it's mixed.
        # Check if we can fix parts of it? For now, SKIP to be safe.
        # logging.warning(f"Skipping {cid} (UnicodeEncodeError): {title}")
        skipped_count += 1
    except UnicodeDecodeError:
        # The bytes we got don't make valid UTF-8
        # logging.warning(f"Skipping {cid} (UnicodeDecodeError): {title}")
        error_count += 1
    except Exception as e:
        logging.error(f"Error {cid}: {e}")
        error_count += 1

conn.commit()
logging.info(f"Done. Updated: {updated_count}, Skipped: {skipped_count}, Errors: {error_count}")

conn.close()
