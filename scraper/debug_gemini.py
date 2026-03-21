import os
import re
import google.generativeai as genai
from pathlib import Path

API_KEY = os.environ.get("GEMINI_API_KEY")
TARGET_FILE = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\lawphil_md\1999\G.R. No. 123780_December_17_1999.md")

def debug_models():
    print("Listing Models:")
    try:
        genai.configure(api_key=API_KEY)
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(m.name)
    except Exception as e:
        print(f"Error listing models: {e}")

def debug_parsing():
    print(f"\nScanning: {TARGET_FILE}")
    if not TARGET_FILE.exists():
        print("File not found.")
        return

    with open(TARGET_FILE, 'r', encoding='utf-8') as f:
        lines = [f.readline() for _ in range(20)]
        
    date_pattern = re.compile(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s+(\d{4})', re.IGNORECASE)
    
    print("Lines read:")
    for i, line in enumerate(lines):
        line = line.strip()
        print(f"L{i}: '{line}'")
        
        # Test match
        if line.startswith("###") or line.startswith("**"):
            print(f"  -> Starts with marker. Testing Regex...")
            match = date_pattern.search(line)
            if match:
                print(f"  -> MATCH: {match.groups()}")
            else:
                print(f"  -> NO MATCH")

if __name__ == "__main__":
    debug_models()
    debug_parsing()
