import sys
import os
import json
import logging

# Add 'api' directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'api')))

import azure.functions as func
import psycopg2
from psycopg2.extras import RealDictCursor

# Import the blueprint/route
from blueprints.codex import get_codex_versions

class MockHttpRequest(func.HttpRequest):
    def __init__(self, params):
        self._params = params
        
    @property
    def params(self):
        return self._params
        
    def get_body(self):
        return b''

def main():
    logging.basicConfig(level=logging.INFO)
    try:
        # Simulate /api/codex/versions?short_name=ROC
        req = MockHttpRequest(params={'short_name': 'ROC'})
        res = get_codex_versions(req)
        
        print(f"Status Code: {res.status_code}")
        body = json.loads(res.get_body().decode('utf-8'))
        
        # Look for links (handle both dict and list responses)
        articles = body if isinstance(body, list) else body.get('articles', [])
        print(f"Total articles returned: {len(articles)}")
        
        match_count = 0
        for art in articles:
            links = art.get('paragraph_links', {})
            anum = art.get('article_num')   # Dedicated endpoint uses article_num
            if anum and ("Rule 10" in anum):
                print(f"Found Article_Num in response: '{anum}' | Links: {links}")
            if links:
                match_count += 1
                     
        print(f"Articles with paragraph_links populated: {match_count}")
        if match_count > 0:
             print("✅ LINK COUNT ATTACHMENT VERIFIED SUCCESSFUL!")
        else:
             print("❌ NO LINKS FOUND IN API RESPONSE!")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error simulating API: {e}")

if __name__ == "__main__":
    main()
