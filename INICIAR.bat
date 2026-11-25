@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (echo Ejecuta INSTALAR.bat primero.& pause & exit /b 1)
start "" http://localhost:8000
.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
pause
