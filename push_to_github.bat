@echo off
title Pushing to GitHub (aditi969/MahaRera_Scrapping_Webapp)...
cd /d "%~dp0"
echo ======================================================
echo Pushing RERA INSIGHT to GitHub:
echo https://github.com/aditi969/MahaRera_Scrapping_Webapp
echo ======================================================

git config user.name "aditi969"
git config user.email "aditi@sigmavalue.co.in"
git remote set-url origin https://github.com/aditi969/MahaRera_Scrapping_Webapp.git

git add .
git commit -m "feat: complete scraper enhancements, date fallbacks, and one-click startup scripts"
git push -u origin main --force

echo ======================================================
echo If push succeeded, your repository is now up to date!
echo ======================================================
pause
