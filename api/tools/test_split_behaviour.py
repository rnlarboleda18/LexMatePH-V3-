import sys
import re

sys.path.append(r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\api')

# Simulate exact Row 9 - Row 10 boundary
prev_content = """SECTION 6. The separation of Church and State shall be inviolable.

State Policies"""

# 1. Correct Split
segs_correct = [p.strip() for p in prev_content.split('\n\n') if p.strip()]
print(f"Correct split: {segs_correct}")

# 2. Lit split (what is currently in file)
segs_lit = [p.strip() for p in prev_content.split('\\n\\n') if p.strip()]
print(f"Literal split: {segs_lit}")
