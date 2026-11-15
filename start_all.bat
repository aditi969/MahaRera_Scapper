@echo off
title RERA INSIGHT - Master Launcher
cd /d "%~dp0"
echo ================================================================
echo   RERA INSIGHT - Maharashtra Real Estate Intelligence Platform
echo   Launching Backend API (Port 8000) and Frontend UI (Port 3000)
echo ================================================================
echo.

:: 1. Launch Backend API in a separate window
echo [1/3] Starting Backend API Server (FastAPI)...
start "RERA INSIGHT - Backend API Server" cmd /k "run_backend.bat"

:: 2. Wait 3 seconds for backend to initialize
echo [2/3] Waiting for backend to initialize...
timeout /t 3 /nobreak >nul

:: 3. Launch Frontend UI in a separate window
echo [3/3] Starting Frontend Web Interface (Next.js)...
start "RERA INSIGHT - Frontend Web UI" cmd /k "run_frontend.bat"

:: 4. Open default web browser
echo.
echo Opening browser at http://localhost:3000 ...
timeout /t 2 /nobreak >nul
start http://localhost:3000

echo ================================================================
echo   Both services are now running!
echo   - Web UI:      http://localhost:3000
echo   - Backend API: http://127.0.0.1:8000/docs
echo.
echo   Keep the two launched command windows open while using the app.
echo ================================================================
