"""Insert missing codal_case_link: People v. XXX262846 → CONST III-21 (double jeopardy).

People v. XXX262846, G.R. No. 262846 (2025-02-18), case_id=64116.
This case abandons People v. Balunsat and establishes that an accused who
appeals a conviction waives double jeopardy protection — a landmark 2025 ruling
directly on Art. III, Sec. 21 of the Constitution.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(os.environ["DB_CONNECTION_STRING"])
cur = conn.cursor(cursor_factory=RealDictCursor)

CASE_ID = 64116
LINKS_TO_ADD = [
    # statute_id, provision_id, specific_ruling
    ("CONST", "III-21",
     "Accused who appeals a conviction waives double jeopardy; appellate court "
     "may convict of a higher offense if warranted — People v. Balunsat abandoned."),
]

for statute_id, provision_id, specific_ruling in LINKS_TO_ADD:
    # Check if link already exists
    cur.execute(
        "SELECT id FROM codal_case_links WHERE case_id=%s AND statute_id=%s AND provision_id=%s",
        (CASE_ID, statute_id, provision_id)
    )
    existing = cur.fetchone()
    if existing:
        print(f"SKIP (already exists): {statute_id}/{provision_id}")
        continue
    cur.execute(
        """INSERT INTO codal_case_links (case_id, statute_id, provision_id, specific_ruling, subject_area)
           VALUES (%s, %s, %s, %s, %s)""",
        (CASE_ID, statute_id, provision_id, specific_ruling, "remedial")
    )
    print(f"INSERTED: case_id={CASE_ID} -> {statute_id}/{provision_id}")

conn.commit()
cur.close()
conn.close()
print("Done.")
