import sys
sys.path.append('data/CodexPhil/scripts')
from process_amendment import get_db_connection

conn = get_db_connection()
cur = conn.cursor()

# Get Article 62 current version
cur.execute("""
    SELECT content 
    FROM article_versions 
    WHERE article_number = '62' 
    AND valid_to IS NULL 
    AND code_id = (SELECT code_id FROM legal_codes WHERE short_name = 'RPC')
""")

content = cur.fetchone()[0]

print("="*80)
print("ARTICLE 62 CONTENT FROM DATABASE")
print("="*80)
print(f"Total length: {len(content)} chars")
print(f"Newline count: {content.count(chr(10))}")
print(f"Carriage return count: {content.count(chr(13))}")
print(f"Double newline count: {content.count(chr(10)+chr(10))}")
print("="*80)
print("FIRST 1000 CHARACTERS (with visible newlines):")
print("="*80)
# Replace newlines with visible markers
preview = content[:1000].replace('\n', '\\n\n').replace('\r', '\\r')
print(preview)
print("="*80)

conn.close()
