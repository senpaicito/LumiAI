@echo off
title Lumi AI - Ollama Server
echo Starting Ollama Server for Lumi AI Companion...
echo.

REM Check if Ollama is installed
where ollama >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Ollama is not installed or not in PATH
    echo Please install Ollama from: https://ollama.ai/
    pause
    exit /b 1
)

REM Check if Ollama is already running
curl -s http://localhost:11434/api/tags >nul 2>nul
if %errorlevel% equ 0 (
    echo Ollama is already running on port 11434
    echo.
) else (
    echo Starting Ollama server...
    start "Ollama Server" /B ollama serve
    timeout /t 5 /nobreak >nul
)

REM Check if model is pulled
echo Checking for Lumi's AI model...
ollama list | findstr "L3.1-Dark-Reasoning" >nul
if %errorlevel% neq 0 (
    echo Model not found. Pulling Lumi's AI model...
    echo This may take a while depending on your internet connection...
    ollama pull hf.co/mradermacher/L3.1-Dark-Reasoning-LewdPlay-evo-Hermes-R1-Uncensored-8B-i1-GGUF:Q6_K
) else (
    echo AI model is ready!
)

echo.
echo Ollama server is running and ready for Lumi AI Companion
echo API available at: http://localhost:11434
echo.
pause