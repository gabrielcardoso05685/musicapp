@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Crie o ambiente virtual seguindo o README.md.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" app.py
pause
