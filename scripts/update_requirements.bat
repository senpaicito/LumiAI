@echo off
title Install Lumi AI Requirements
cd /d "%~dp0.."

echo ========================================
echo    Lumi AI - Requirements Installer
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo Python found, installing requirements...
echo.

REM Upgrade pip first
python -m pip install --upgrade pip

REM Install requirements
pip install -r requirements.txt

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo    Requirements installed successfully!
    echo ========================================
) else (
    echo.
    echo ========================================
    echo    ERROR: Failed to install requirements
    echo ========================================
)

echo.
pause