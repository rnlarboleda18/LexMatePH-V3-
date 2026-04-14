@echo off
REM Unified E-Library pipeline via PowerShell (see Shortcuts.md).
setlocal
cd /d "%~dp0"

where powershell >nul 2>&1
if errorlevel 1 (
  echo PowerShell not found.
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0admin-tools\case-digest-pipeline\Run-ElibCaseDigestPipeline.ps1" %*
set "_ec=%ERRORLEVEL%"
if %_ec% neq 0 pause
exit /b %_ec%
