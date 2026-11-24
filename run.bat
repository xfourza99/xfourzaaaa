@echo off
title CE Amplifier Lab
cd /d "%~dp0"

set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 goto :fallback
    "%PY%" -m pip install -r requirements.txt
    if errorlevel 1 goto :fallback
)

echo Starting CE Amplifier Lab at http://127.0.0.1:5000
echo Keep this window open. Press Ctrl+C to stop.
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:5000/?mode=divider"
"%PY%" -m flask --app app run --host 0.0.0.0 --port 5000 --no-reload
goto :eof

:fallback
echo Virtual environment failed; using system Python.
python -m pip install -r requirements.txt
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:5000/?mode=divider"
python -m flask --app app run --host 0.0.0.0 --port 5000 --no-reload
pause
