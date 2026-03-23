import re
import os

def analyze(file_path):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return
        
    print(f"\nAnalyzing: {os.path.basename(file_path)}")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    headers = re.findall(r'Question\s*\(', content, re.IGNORECASE)
    markers = re.findall(r'\nQ\d+:', content)
    sa_markers = re.findall(r'Suggested Answer', content, re.IGNORECASE)
    
    print(f"  Total 'Question (' headers: {len(headers)}")
    print(f"  Total 'Q#: ' markers: {len(markers)}")
    print(f"  Total 'Suggested Answer' markers: {len(sa_markers)}")

files = [
    r"C:\Users\rnlar\.gemini\antigravity\scratch\LexMatePH v3\pdf quamto\ai_md\Quamto 2023 Civil Law_AI.md",
    r"C:\Users\rnlar\.gemini\antigravity\scratch\LexMatePH v3\pdf quamto\ai_md\4_Legal_Ethics_QUAMTO_AI.md",
    r"C:\Users\rnlar\.gemini\antigravity\scratch\LexMatePH v3\pdf quamto\ai_md\2_Criminal_Law_QUAMTO_AI.md"
]

for f in files:
    analyze(f)
