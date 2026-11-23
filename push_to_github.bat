@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
set "PATH=%~dp0..\tools\git\cmd;%PATH%"

echo =====================================================================
echo                MahaRera GitHub Push Utility
echo =====================================================================
echo Repository : https://github.com/aditi969/MahaRera_Scapper.git
echo Target     : origin main
echo =====================================================================
echo.
echo GitHub requires authentication via a Personal Access Token (classic token
echo with 'repo' scope or fine-grained token with Contents read/write).
echo.
set /p "GITHUB_PAT=Enter GitHub Personal Access Token (PAT): "

if "!GITHUB_PAT!"=="" (
    echo.
    echo [INFO] No token entered. Attempting push with default credentials...
    git push -u origin main
) else (
    echo.
    echo [INFO] Pushing commits to GitHub...
    git push -u "https://aditi969:!GITHUB_PAT!@github.com/aditi969/MahaRera_Scapper.git" main
)

echo.
if !ERRORLEVEL! equ 0 (
    echo [SUCCESS] Push completed successfully!
) else (
    echo [ERROR] Push failed. Please verify token permissions and internet connection.
)
echo.
pause
