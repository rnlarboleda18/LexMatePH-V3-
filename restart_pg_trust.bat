@echo off
echo Restarting PostgreSQL with trust auth...
net stop postgresql-x64-16
net start postgresql-x64-16
echo Done! PostgreSQL restarted.
pause
