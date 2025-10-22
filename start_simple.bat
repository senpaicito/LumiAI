@echo off
title Lumi AI Companion
cd /d "%~dp0"

echo ================================
echo    Starting Lumi AI Companion
echo ================================
echo.

if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    echo Installing dependencies...
    venv\Scripts\pip.exe install -r requirements.txt
    echo.
)

echo Starting Lumi...
echo Note: Make sure Ollama is running for AI responses
echo Web Interface: http://localhost:5000
echo.

venv\Scripts\python.exe main.py

echo.
echo Lumi has stopped.
pause