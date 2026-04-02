import os
import requests

# URL of the 1987 Philippine Constitution on the Official Gazette
url = "https://www.officialgazette.gov.ph/constitutions/1987-constitution/"
BASE_DIR = r"c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2"
OUTPUT_PATH = os.path.join(BASE_DIR, "LexCode", "Codals", "html", "CONST_OG_base.html")

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

print(f"Fetching from: {url}")
response = requests.get(url, headers=headers)
response.raise_for_status()

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    f.write(response.text)

print(f"Saved {len(response.text)} characters to {OUTPUT_PATH}")
