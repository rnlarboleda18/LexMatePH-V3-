import psycopg2
import json

try:
    with open('api/local.settings.json') as f:
        settings = json.load(f)
        DB_CONNECTION_STRING = settings['Values']['DB_CONNECTION_STRING']
except:
    DB_CONNECTION_STRING = "postgresql://postgres:password@localhost:5432/sc_decisions"

conn = psycopg2.connect(DB_CONNECTION_STRING)
cur = conn.cursor()

print("Fetching all significance values...")
cur.execute("SELECT id, short_title, digest_significance FROM sc_decided_cases WHERE digest_significance IS NOT NULL")
rows = cur.fetchall()

categories = {
    "LANDMARK": [],
    "STANDARD": [],
    "BLOCKED": [],
    "REITERATION": [],
    "OTHER": []
}

for cid, title, sig in rows:
    s_lower = sig.lower()
    title = (title[:50] + '...') if title and len(title) > 50 else (title or "No Title")
    clean_sig = sig.replace('\n', ' ').strip()[:100] + "..."
    
    if "blocked_safety" in s_lower:
        categories["BLOCKED"].append((cid, title, clean_sig))
    elif "landmark" in s_lower:
        categories["LANDMARK"].append((cid, title, clean_sig))
    elif "standard" in s_lower:
        categories["STANDARD"].append((cid, title, clean_sig))
    elif "reiteration" in s_lower or "reiterate" in s_lower or "affirmed" in s_lower:
        categories["REITERATION"].append((cid, title, clean_sig))
    else:
        categories["OTHER"].append((cid, title, clean_sig))

with open(r"C:\Users\rnlar\.gemini\antigravity\brain\e768aa86-6434-4f77-b82a-5c95636c43ba\significance_audit.md", "w", encoding="utf-8") as f:
    f.write("# Significance Classification Audit\n\n")
    f.write("**Generated:** 2026-01-02\n\n")
    f.write("## Summary Statistics\n")
    f.write(f"- **Total Non-Reiteration:** {len(categories['LANDMARK']) + len(categories['STANDARD']) + len(categories['OTHER']) + len(categories['BLOCKED'])}\n")
    f.write(f"- **Reiteration (Text Match):** {len(categories['REITERATION'])}\n")
    f.write("\n### Breakdown:\n")
    f.write(f"- **Landmark:** {len(categories['LANDMARK'])}\n")
    f.write(f"- **Standard:** {len(categories['STANDARD'])}\n")
    f.write(f"- **Blocked Safety:** {len(categories['BLOCKED'])}\n")
    f.write(f"- **Other (Unclassified/Descriptions):** {len(categories['OTHER'])}\n\n")
    
    f.write("---\n")
    
    f.write("## Top Results by Category\n\n")

    f.write("### 🏛️ LANDMARK CASES (Sample)\n")
    f.write("| ID | Case Title | Snippet |\n")
    f.write("|----|------------|---------|\n")
    for row in categories["LANDMARK"][:50]:
        f.write(f"| {row[0]} | {row[1]} | {row[2]} |\n")
    f.write("\n")

    f.write("### ⚖️ STANDARD CASES (Sample)\n")
    f.write("| ID | Case Title | Snippet |\n")
    f.write("|----|------------|---------|\n")
    for row in categories["STANDARD"][:50]:
        f.write(f"| {row[0]} | {row[1]} | {row[2]} |\n")
    f.write("\n")
    
    f.write("### ❓ OTHER / UNCLASSIFIED (Sample)\n")
    f.write("> These contain descriptions but no clear 'Reiteration' or 'Landmark' keyword.\n\n")
    f.write("| ID | Case Title | Snippet |\n")
    f.write("|----|------------|---------|\n")
    for row in categories["OTHER"][:50]:
        f.write(f"| {row[0]} | {row[1]} | {row[2]} |\n")
    f.write("\n")
    
    f.write("### 🚫 BLOCKED SAFETY (Sample)\n")
    f.write("| ID | Case Title | Snippet |\n")
    f.write("|----|------------|---------|\n")
    for row in categories["BLOCKED"][:50]:
        f.write(f"| {row[0]} | {row[1]} | {row[2]} |\n")

print("Report generated.")
conn.close()
