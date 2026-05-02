@echo off
cd /d "C:\Users\rnlar\.gemini\antigravity\scratch\LexMatePH v3"
git push origin main > push_output.log 2>&1
echo Exit code: %ERRORLEVEL% >> push_output.log
