@echo off
chcp 65001 >nul
cd /d "%~dp0"
title YouTube TR - Sunucu
REM Script icinde Enter ile duraklatma var; burada da pause (cift guvenlik).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run-local.ps1"
set ERR=%ERRORLEVEL%
echo.
echo [CMD] PowerShell cikti. Kod: %ERR%
echo Pencereyi kapatmak icin bir tusa basin...
pause
