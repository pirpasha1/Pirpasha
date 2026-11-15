@echo off
REM Double-click this file to start the School Management System on Windows.
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python is not installed. Please install it from https://www.python.org/downloads/
  echo During installation, tick "Add Python to PATH".
  pause
  exit /b
)
if not exist ".venv" (
  echo First run: setting up, please wait...
  python -m venv .venv
  .venv\Scripts\python -m pip install --quiet -r requirements.txt
)
.venv\Scripts\python run.py %*
pause
