@echo off
REM Double-click to start: records now (press Enter to stop), then transcribes + summarizes.
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (
    echo Virtual environment not found. Run setup.ps1 first.
    pause
    exit /b 1
)
venv\Scripts\python.exe run.py %*
pause
