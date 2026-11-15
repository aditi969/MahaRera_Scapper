@echo off
title RERA INSIGHT - Frontend Web UI (Port 3000)
cd /d "%~dp0frontend"
echo ================================================================
echo   RERA INSIGHT - Starting Next.js Web Interface
echo ================================================================
echo.

if not exist "node_modules" (
    echo [NOTICE] First time setup: installing frontend npm packages...
    call npm install
)

call npm run dev
if errorlevel 1 (
    echo.
    echo [ERROR] Frontend failed to start.
    echo Please ensure Node.js is installed:
    echo     cd frontend ^&^& npm install
    echo.
    pause
)
