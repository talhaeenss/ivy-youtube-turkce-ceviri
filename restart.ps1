# Portu dinleyen sureci kapatir, ardindan run-local.ps1 ile sunucuyu yeniden baslatir.
$ErrorActionPreference = "Continue"

$root = $PSScriptRoot
$listenPort = 8000
if ($env:YT_TR_PORT -match '^\d+$') {
    $listenPort = [int]$env:YT_TR_PORT
}

Write-Host ""
$freeScript = Join-Path $root "free-yt-port.ps1"
if (-not (Test-Path $freeScript)) {
    Write-Error "free-yt-port.ps1 bulunamadi: $freeScript"
    exit 1
}
. $freeScript
Write-Host ('>>> Port ' + $listenPort + ' hizli temizlik (tam mantik ve gerekirse baska port run-local.ps1 icinde)...') -ForegroundColor Yellow
$null = Clear-YtListenPort -Port $listenPort -MaxAttempts 2
# Basarisiz olsa bile cikma: run-local yeniden dener; olmazsa otomatik bos porta gecer (YT_TR_NO_AUTO_PORT=1 ile kapatilir).

$runLocal = Join-Path $root "run-local.ps1"
if (-not (Test-Path $runLocal)) {
    Write-Error "run-local.ps1 bulunamadi: $runLocal"
    exit 1
}

Write-Host ">>> Sunucu baslatiliyor (run-local.ps1 ayri PowerShell surecinde)..." -ForegroundColor Cyan
Write-Host "    Bu CMD penceresini KAPATMAYIN - sunucu o alt surecte calisir." -ForegroundColor DarkGray
Write-Host ""

# NOT: & $runLocal AYNI oturumda calisirsa run-local.ps1 sonundaki 'exit' bu scripti de oldurur;
# restart.ps1'deki satirlar ve restart.bat'taki pause hic calismaz gibi gorunebilir.
$code = 0
try {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $runLocal
    if ($null -ne $LASTEXITCODE) { $code = $LASTEXITCODE }
} catch {
    Write-Host ""
    Write-Host ">>> Hata: $_" -ForegroundColor Red
    $code = 1
}

Write-Host ""
if ($code -ne 0) {
    Write-Host ">>> Alt surec cikis kodu: $code (port, Python, pip - yukariyi okuyun)" -ForegroundColor Red
} else {
    Write-Host ">>> Alt surec normal cikti." -ForegroundColor DarkGray
}
exit $code
