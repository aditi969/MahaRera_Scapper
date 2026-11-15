@echo off
title Pushing to GitHub (mayankvispute7/Scrapper)...
echo ======================================================
echo Pushing RERA INSIGHT and Documentation to GitHub:
echo https://github.com/mayankvispute7/Scrapper
echo ======================================================
git remote set-url origin https://github.com/mayankvispute7/Scrapper.git
git push -u origin main
echo ======================================================
echo If push succeeded, your repository is now up to date!
echo ======================================================
pause
