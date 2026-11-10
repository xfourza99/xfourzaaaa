@echo off
title BJT CE Bias Web App
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
    echo Creating virtual environment...
    python -m venv .venv
    .venv\Scripts\python -m pip install -r requirements.txt
)
echo Starting server at http://127.0.0.1:5000
echo Keep this window open. Press Ctrl+C to stop.
.venv\Scripts\python.exe app.py
pause