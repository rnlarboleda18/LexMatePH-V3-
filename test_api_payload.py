import os
import json
import sys

sys.path.insert(0, os.path.abspath('api'))

class MockBlueprint:
    def route(self, *args, **kwargs): return lambda f: f
import azure.functions as func
func.Blueprint = MockBlueprint

from blueprints.const import get_const_by_book

def test_api_payload():
    with open('api/local.settings.json', 'r') as f:
         config = json.load(f)
         os.environ["DB_CONNECTION_STRING"] = config.get('Values', {}).get('DB_CONNECTION_STRING')

    print("--- FETCHING /api/const/book/1 ---")
    try:
        req = func.HttpRequest("GET", "http://localhost", route_params={"book_num": "1"}, body=b"")
        res = get_const_by_book(req)
        body = res.get_body().decode('utf-8')
        data = json.loads(body)
        
        # Print first 40 items structure
        for i, item in enumerate(data[:40]):
             if i < 10 or 'I-0' in str(item) or 'III-1' in str(item):
                  print(f"[{i}] Num: {item.get('article_num')} | Key ID: {item.get('key_id')} | Title: {item.get('article_title')} | Label: {item.get('article_label')}")
        
    except Exception as e:
         print(f"Error: {e}")

if __name__ == "__main__":
    test_api_payload()
