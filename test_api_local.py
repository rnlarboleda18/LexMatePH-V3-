import urllib.request
import json
try:
    with urllib.request.urlopen("http://localhost:7071/api/const/book/1") as response:
        data = json.loads(response.read().decode())
        for item in data:
            if item.get('key_id', '').startswith('II-'):
                print(f"ID: {item.get('key_id')}")
                print(f"  group_header: {repr(item.get('group_header'))}")
                print(f"  section_label: {repr(item.get('section_label'))}")
                print(f"  article_title: {repr(item.get('article_title'))}")
                print(f"  chapter_label: {repr(item.get('chapter_label'))}")
                print(f"  title_label: {repr(item.get('title_label'))}")
                print(f"  book_label: {repr(item.get('book_label'))}")
                print(f"  content_md (first 50 chars): {repr(item.get('content_md', '')[:50])}")
except Exception as e:
    print(f"Error: {e}")
