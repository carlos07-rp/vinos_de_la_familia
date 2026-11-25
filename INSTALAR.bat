@echo off
cd /d "%~dp0"
py -m venv .venv
if errorlevel 1 goto end
.venv\Scripts\python.exe -m pip install -r requirements.txt
:end
pause
