@echo off
chcp 65001 >nul
cd /d "%~dp0"
title YouTube TR - Sunucu
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0restart.ps1"
set ERR=%ERRORLEVEL%
echo.
if %ERR% neq 0 (
  echo [HATA] Cikis kodu: %ERR%
) else (
  echo Sunucu durdu ^(Ctrl+C veya normal cikis^).
)
echo.
echo Pencereyi kapatmak icin bir tusa basin...
pause
