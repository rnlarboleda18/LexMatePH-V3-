import re
import os

files = [
    r"c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\CodexPhil\Codals\md\ROC\1. ROC Civil Procedure as amended 2019_fixed_chunked.md",
    r"c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\CodexPhil\Codals\md\ROC\2. ROC Special Proceeding.md",
    r"c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\CodexPhil\Codals\md\ROC\3. ROC Criminal Procedure.md",
    r"c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\CodexPhil\Codals\md\ROC\4. ROC Evidence as amended 2019.md"
]

section_pattern = re.compile(r'^Section\s+(\d+)\.(.*)', re.IGNORECASE)

with open('scripts/test_output_split.txt', 'w', encoding='utf-8') as log:
    def test_file(file_path):
        if not os.path.exists(file_path):
             return
        with open(file_path, 'r', encoding='utf-8') as f:
             lines = f.readlines()
             
        fails = []
        log.write(f"\nScanning: {os.path.basename(file_path)}\n")
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            sec_match = section_pattern.match(line_stripped)
            if sec_match:
                 rest = sec_match.group(2).strip()
                 
                 # The new regex
                 sep_match = re.search(r'^(.*?)\s+[–—\-]\s+(.*)', rest)
                 if not sep_match:
                     if len(rest) > 2 and rest.endswith('.'):
                          pass
                     else:
                          fails.append((i+1, rest))

        for f_line, f_rest in fails[:5]:
             log.write(f"  Fail at Line {f_line}: {f_rest}\n")
        log.write(f"  Total fails that might exceed title length or drop content: {len(fails)}\n")

    for f_path in files:
        test_file(f_path)
