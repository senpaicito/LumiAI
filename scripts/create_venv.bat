@echo off
title Lumi AI - Virtual Environment Setup
echo ========================================
echo    Lumi AI Virtual Environment Creator
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo.
    echo Please install Python 3.8+ from:
    echo https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo ✓ Python found:
python --version

REM Check Python version
python -c "import sys; print('Python version check: ' + str(sys.version_info[:2])); exit(0) if sys.version_info >= (3, 8) else exit(1)"
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Python 3.8 or higher is required
    echo Current version:
    python --version
    echo.
    echo Please upgrade your Python installation.
    echo.
    pause
    exit /b 1
)

echo ✓ Python version is compatible (3.8+)
echo.

REM Set project root
set "PROJECT_ROOT=%~dp0.."
cd /d "%PROJECT_ROOT%"

echo Project directory: %CD%
echo.

REM Check if virtual environment already exists
if exist "venv" (
    echo Virtual environment already exists.
    echo.
    choice /C YN /M "Do you want to recreate it? (Y/N)"
    if %errorlevel% equ 2 (
        echo Keeping existing virtual environment.
        goto activate_env
    )
    
    echo.
    echo Removing existing virtual environment...
    rmdir /s /q "venv"
    if %errorlevel% neq 0 (
        echo ERROR: Failed to remove existing virtual environment
        echo Please close any Python applications and try again.
        echo.
        pause
        exit /b 1
    )
    echo ✓ Old virtual environment removed
)

echo.
echo Creating new virtual environment...
python -m venv venv

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to create virtual environment
    echo This might be due to:
    echo - Missing venv module (install python3-venv on Linux)
    echo - Permission issues
    echo - Corrupted Python installation
    echo.
    pause
    exit /b 1
)

echo ✓ Virtual environment created successfully
echo.

:activate_env
echo Activating virtual environment...
call venv\Scripts\activate.bat

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to activate virtual environment
    echo.
    pause
    exit /b 1
)

echo ✓ Virtual environment activated
echo.

echo Upgrading pip to latest version...
python -m pip install --upgrade pip

if %errorlevel% neq 0 (
    echo.
    echo WARNING: Failed to upgrade pip, but continuing...
) else (
    echo ✓ Pip upgraded successfully
)

echo.
echo ========================================
echo    Installing Project Dependencies
echo ========================================
echo.

REM Check if requirements file exists
if not exist "requirements.txt" (
    echo ERROR: requirements.txt not found!
    echo Please make sure you're in the correct directory.
    echo.
    pause
    exit /b 1
)

echo Installing from requirements.txt...
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Some dependencies failed to install
    echo.
    echo Common solutions:
    echo 1. Make sure you have Visual C++ Build Tools installed
    echo 2. Try running as Administrator
    echo 3. Check your internet connection
    echo.
    echo You can try installing manually with:
    echo pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo.
echo ✓ All dependencies installed successfully!
echo.

echo ========================================
echo    Environment Setup Complete!
echo ========================================
echo.
echo Virtual environment is ready to use!
echo.
echo Next steps:
echo 1. Make sure Ollama is running
echo 2. Start Lumi with: scripts\start_lumi.bat
echo 3. Access the WebUI at: http://localhost:5000
echo.
echo Your virtual environment is located at:
echo %CD%\venv
echo.
echo To activate manually in the future:
echo - Navigate to: %CD%
echo - Run: venv\Scripts\activate.bat
echo.
pause