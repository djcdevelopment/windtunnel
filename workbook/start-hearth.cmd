@echo off
cd /d C:\hearth
echo [%date% %time%] HEARTH starting >> hearth.log
venv\Scripts\python.exe hearth_gateway.py >> hearth.log 2>&1
