@echo off
setlocal
set "API=C:\Users\rnlar\.gemini\antigravity\scratch\LexMatePH v3\api"
set "REPO=C:\Users\rnlar\.gemini\antigravity\scratch\LexMatePH v3"
set PY=C:\Users\rnlar\AppData\Local\Programs\Python\Python312\python.exe
set LOGS=%~dp0logs
set "GOOGLE_APPLICATION_CREDENTIALS=%REPO%\lexmateph-rag-key.json"

echo [%TIME%] Starting civil >> "%LOGS%\run_remaining2.log"
"%PY%" "%API%\tools\generate_bar_reviewer.py" --subject civil >> "%LOGS%\civil_final2.log" 2>&1
echo [%TIME%] civil done (exit %ERRORLEVEL%) >> "%LOGS%\run_remaining2.log"

"%PY%" "%API%\tools\publish_all_subjects.py" >> "%LOGS%\run_remaining2.log" 2>&1

echo [%TIME%] Starting labor >> "%LOGS%\run_remaining2.log"
"%PY%" "%API%\tools\generate_bar_reviewer.py" --subject labor >> "%LOGS%\labor_final2.log" 2>&1
echo [%TIME%] labor done (exit %ERRORLEVEL%) >> "%LOGS%\run_remaining2.log"

"%PY%" "%API%\tools\publish_all_subjects.py" >> "%LOGS%\run_remaining2.log" 2>&1

echo [%TIME%] Starting commercial >> "%LOGS%\run_remaining2.log"
"%PY%" "%API%\tools\generate_bar_reviewer.py" --subject commercial >> "%LOGS%\commercial_final2.log" 2>&1
echo [%TIME%] commercial done (exit %ERRORLEVEL%) >> "%LOGS%\run_remaining2.log"

"%PY%" "%API%\tools\publish_all_subjects.py" >> "%LOGS%\run_remaining2.log" 2>&1

echo [%TIME%] ALL DONE >> "%LOGS%\run_remaining2.log"
