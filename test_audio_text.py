import sys
import os
import re
sys.path.insert(0, os.path.abspath('api'))
sys.path.insert(0, os.path.abspath('api/blueprints'))
import audio_provider

text8, err8 = audio_provider._get_text_for_codal('8', 'FC')
text7, err7 = audio_provider._get_text_for_codal('7', 'FC')

print("--- ARTICLE 8 TEXT ---")
if err8: print("ERROR:", err8)
else: print(repr(text8))

print("--- ARTICLE 7 TEXT ---")
if err7: print("ERROR:", err7)
else: print(repr(text7))

import db_pool
conn = db_pool.get_db_connection()
cur = conn.cursor()
cur.execute("SELECT id, article_num, content_md FROM fc_codal WHERE article_num IN ('FC-I-7', 'FC-I-8')")
for r in cur.fetchall():
    print(r[1], repr(r[2][:50]))
conn.close()
