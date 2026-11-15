@echo off
title RERA INSIGHT - Dependency Setup
cd /d "%~dp0"
echo ================================================================
echo   RERA INSIGHT - Installing Python and Node Dependencies
echo ================================================================
echo.

echo [1/2] Installing Python backend & scraper packages...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install Python packages. Please ensure Python is installed and added to PATH.
    pause
    exit /b 1
)

echo.
echo [2/2] Installing Frontend Node.js packages...
cd frontend
call npm install
if errorlevel 1 (
    echo [ERROR] Failed to install Node packages. Please ensure Node.js is installed.
    pause
    exit /b 1
)

echo.
echo ================================================================
echo   All dependencies installed successfully!
echo   You can now launch the app using: start_all.bat
echo ================================================================
pause
