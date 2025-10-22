@echo off
title Lumi AI Companion
cd /d "%~dp0.."

echo Starting Lumi AI Companion...
echo.

REM Basic checks
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

echo Starting Lumi...
python main.py

echo.
echo Lumi has stopped. Press any key to close.
pause >nul