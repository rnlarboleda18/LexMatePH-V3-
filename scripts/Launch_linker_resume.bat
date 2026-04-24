@echo off
REM Double-click this file to open a NEW window and run the RPC/RCC linker (2020 then 2019).
cd /d "%~dp0"
start "LexMate codal linker 2020+2019" powershell.exe -NoExit -ExecutionPolicy Bypass -File "%~dp0resume_linker_2020_2019.ps1"
