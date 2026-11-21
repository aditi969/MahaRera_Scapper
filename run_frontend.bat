@echo off
title RERA INSIGHT - Frontend Web UI (Port 3000)
if exist "%~dp0..\tools\node-v20.18.0-win-x64" (
    set "PATH=%~dp0..\tools\node-v20.18.0-win-x64;%PATH%"
)
if exist "%~dp0tools\node-v20.18.0-win-x64" (
    set "PATH=%~dp0tools\node-v20.18.0-win-x64;%PATH%"
)

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
