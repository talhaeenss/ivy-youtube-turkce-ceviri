@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
cls

echo ==========================================
echo          Git Push Tool
echo ==========================================
echo.

git status --porcelain >nul 2>&1
if errorlevel 1 (
    echo HATA: Bu klasor bir git repository degil!
    pause
    exit /b 1
)

echo Mevcut degisiklikler:
echo ------------------
git status --short
echo.

git diff-index --quiet HEAD --
if errorlevel 1 (
    set /p msg=Commit mesajini gir: 
    
    if "!msg!"=="" (
        echo HATA: Commit mesaji bos olamaz!
        pause
        exit /b 1
    )
    
    echo.
    echo Dosyalar ekleniyor...
    git add .
    
    echo Commit yapiliyor...
    git commit -m "!msg!"
    
    if errorlevel 1 (
        echo HATA: Commit basarisiz!
        pause
        exit /b 1
    )
    
    echo GitHub'a pushlaniyor...
    git push origin main
    
    if errorlevel 1 (
        echo HATA: Push basarisiz!
        echo Git remote durumunu kontrol edin.
        pause
        exit /b 1
    )
    
    echo.
    echo ==========================================
    echo   BASARILI! Tum degisiklikler pushlandi
    echo ==========================================
) else (
    echo Pushlanacak degisiklik bulunamadi.
    echo Repository zaten guncel durumda.
)

echo.
pause
