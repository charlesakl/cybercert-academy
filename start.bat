@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Creating local Python environment...
  py -3.12 -m venv .venv 2>nul
  if errorlevel 1 (
    echo Python 3.12 not found. Trying another installed Python 3 version...
    py -3 -m venv .venv
  )
  if not exist ".venv\Scripts\python.exe" (
    echo Could not create .venv. Install Python 3.12 or create it manually.
    pause
    exit /b 1
  )
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (pause & exit /b 1)
".venv\Scripts\python.exe" -m streamlit run app.py
pause
