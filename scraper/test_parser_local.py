from content_parser import parse_decision_content
import json
import os

with open("downloads/1927/january/1.html", "r", encoding="utf-8") as f:
    html = f.read()
    
data = parse_decision_content(html)
# Verify structure (simulate download_decisions.py behavior)
final_output = {
    "case_number": "TEST-G.R. No. 123",
    "year": 1927,
    "main_text": data.get("main_text", "")
}

with open("test_output.json", "w", encoding="utf-8") as f:
    json.dump(final_output, f, indent=2, ensure_ascii=False)
print("Output written to test_output.json")
