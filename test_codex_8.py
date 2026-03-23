import sys
import os
import json
sys.path.insert(0, os.path.abspath('api'))
sys.path.insert(0, os.path.abspath('api/blueprints'))
import codex

out, err = codex.get_codex('FC')
print("Error:", err)
print("Finding Article 7 and 8 in the response:")
for ch in out:
    for art in ch.get('articles', []):
        if art.get('article_number') in ('7', '8'):
            print(f"Article {art.get('article_number')}: ID={art.get('id')} - {art.get('content')[:50]}...")
