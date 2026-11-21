@echo off
title RERA INSIGHT - Backend API Server (Port 8000)
cd /d "%~dp0"
echo ================================================================
echo   RERA INSIGHT - Starting FastAPI Backend Server
echo ================================================================
echo.

:: Check if port 8000 is already in use and free it if needed
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    echo [NOTICE] Port 8000 is occupied by PID %%a. Freeing port 8000...
    taskkill /F /T /PID %%a >nul 2>&1
)
timeout /t 2 /nobreak >nul

set PYTHON_CMD=python
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYTHON_CMD=%~dp0.venv\Scripts\python.exe"
)

"%PYTHON_CMD%" run_backend.py
if errorlevel 1 (
    echo.
    echo [ERROR] Backend failed to start.
    echo Please ensure dependencies are installed:
    echo     pip install -r requirements.txt
    echo.
    pause
)
