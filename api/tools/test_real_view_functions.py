import sys
import json

sys.path.append(r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\api')

from blueprints.const import get_articles_const, get_family_code

class MockRequest:
    pass

def test():
    print("\n--- TESTING CONSTITUTION ---")
    try:
        # get_articles_const expects book_num in route, but it gets injected by Azure
        # Let's see if we can call it. Wait, the definition is:
        # def get_articles_const(req: func.HttpRequest) -> func.HttpResponse:
        # Wait! get_articles_const doesn't accept book_num in arguments!
        res = get_articles_const(MockRequest())
        print(f"Status: {res.status_code}")
        body = res.get_body().decode('utf-8')
        data = json.loads(body)
        print(f"Count: {len(data)}")
        if len(data) > 0:
             print(f"First element: {data[0]['article_title'] if 'article_title' in data[0] else 'No title'}")
    except Exception as e:
        print(f"Exception Const: {e}")

    print("\n--- TESTING FAMILY CODE ---")
    try:
        res = get_family_code(MockRequest())
        print(f"Status: {res.status_code}")
        body = res.get_body().decode('utf-8')
        data = json.loads(body)
        print(f"Count: {len(data)}")
    except Exception as e:
        print(f"Exception FC: {e}")

test()
