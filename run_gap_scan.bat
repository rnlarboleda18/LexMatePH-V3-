@echo off
cd /d "C:\Users\rnlar\.gemini\antigravity\scratch\LexMatePH v3"
"C:\Users\rnlar\.gemini\antigravity\scratch\LexMatePH v3\.venv\Scripts\python.exe" -u scripts\scan_elib_gaps.py > "admin-tools\case-digest-pipeline\gap_scan.log" 2>&1
