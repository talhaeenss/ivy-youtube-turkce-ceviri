# Yerel kullanım: backend icin venv olusturur, bagimliliklari kurar, sunucuyu baslatir.
$ErrorActionPreference = "Stop"
# Windows konsolunda transcribe.py vb. emoji/cikti hatasini onler
$env:PYTHONUTF8 = "1"
$root = $PSScriptRoot
$backend = Join-Path $root "backend"
$venvDir = Join-Path $backend ".venv"
$py = Join-Path $venvDir "Scripts\python.exe"

if (-not (Test-Path $backend)) {
    Write-Error "backend klasoru bulunamadi: $backend"
}

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    Write-Error "Python Launcher (py) bulunamadi. python.org'dan Python 3.10+ kurun."
}

if (-not (Test-Path $py)) {
    Write-Host ">>> Ilk kurulum: sanal ortam olusturuluyor (Python 3.13)..."
    # Bu sistemde ensurepip bozuk olabiliyor; pip'i sonra get-pip ile yukluyoruz
    py -3.13 -m venv --without-pip $venvDir
}

$prevEa = $ErrorActionPreference
$ErrorActionPreference = "SilentlyContinue"
$null = & $py -m pip --version 2>&1
$pipOk = ($LASTEXITCODE -eq 0)
$ErrorActionPreference = $prevEa
if (-not $pipOk) {
    Write-Host ">>> pip yukleniyor (bir kerelik)..."
    $gp = Join-Path $env:TEMP "get-pip-yt-tr.py"
    Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $gp -UseBasicParsing
    & $py $gp
    if ($LASTEXITCODE -ne 0) { Write-Error "pip kurulamadi." }
}

Set-Location $backend

Write-Host ">>> Paketler kontrol ediliyor (ilk seferde uzun surebilir)..."
& $py -m pip install --upgrade pip -q
& $py -m pip install -r "requirements.txt"

Write-Host ">>> Backend klasoru: $backend" -ForegroundColor DarkGray
Write-Host ">>> Python: $py" -ForegroundColor DarkGray
if (-not (Test-Path (Join-Path $backend "main.py"))) {
    Write-Error "main.py bulunamadi: $backend"
}
$env:YT_TR_LOG = "info"

$listenPort = 8000
if ($env:YT_TR_PORT -match '^\d+$') {
    $listenPort = [int]$env:YT_TR_PORT
}
$env:YT_TR_PORT = "$listenPort"

# Port doluysa: Stop-Process yetkisiz kalabiliyor; free-yt-port.ps1 taskkill + tekrar kontrol eder (WinError 10048 onlenir).
# Istemezseniz: $env:YT_TR_NO_PORT_KILL="1"
$noKill = ($env:YT_TR_NO_PORT_KILL -eq "1")
if (-not $noKill) {
    $freeScript = Join-Path $root "free-yt-port.ps1"
    if (-not (Test-Path $freeScript)) {
        throw "free-yt-port.ps1 bulunamadi: $freeScript"
    }
    $prevEa2 = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        . $freeScript
        Write-Host ""
        $portOk = Clear-YtListenPort -Port $listenPort -MaxAttempts 3
        if (-not $portOk) {
            if ($env:YT_TR_NO_AUTO_PORT -eq "1") {
                throw "Port $listenPort bosaltilamadi. Yonetici CMD ile taskkill, veya `$env:YT_TR_PORT=8010` veya YT_TR_NO_AUTO_PORT kaldirilip tekrar deneyin."
            }
            $scanFrom = $listenPort + 1
            $scanTo = $listenPort + 50
            $alt = Get-YtFirstFreeTcpPort -FromPort $scanFrom -ToPort $scanTo
            if ($null -eq $alt) {
                throw "Port $listenPort bosaltilamadi ve $scanFrom-$scanTo arasinda bos dinleyici yok."
            }
            Write-Host ""
            Write-Host ('*** OTOMATIK PORT: ' + $listenPort + ' kapatilamadi (genelde Yonetici/SYSTEM sureci); sunucu ' + $alt + ' ile acilacak.') -ForegroundColor Yellow
            Write-Host ('*** Tarayici: http://127.0.0.1:' + $alt + '/') -ForegroundColor White
            Write-Host '*** Eklenti hala 8000 bekliyorsa bu calistirmada paneli yukaridaki adresten acin.' -ForegroundColor DarkYellow
            Write-Host ""
            $listenPort = $alt
            $env:YT_TR_PORT = "$listenPort"
        }
    } finally {
        $ErrorActionPreference = $prevEa2
    }
} else {
    $busy = Get-NetTCPConnection -LocalPort $listenPort -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($busy) {
        Write-Host ""
        Write-Host "!!! UYARI: Port $listenPort dolu (YT_TR_NO_PORT_KILL=1). Gerekirse el ile kapat veya restart.bat kullan." -ForegroundColor Red
        Write-Host ""
    }
}

$browserUrl = "http://127.0.0.1:$listenPort/"
Write-Host ""
Write-Host "========================================"  -ForegroundColor Cyan
Write-Host "  PORT: $listenPort" -ForegroundColor Cyan
Write-Host "  Tarayici (web paneli + API):" -ForegroundColor Cyan
Write-Host "  $browserUrl" -ForegroundColor White
Write-Host "  JSON API ozeti: http://127.0.0.1:$listenPort/api/info" -ForegroundColor DarkGray
Write-Host "  Swagger (tum endpointler): http://127.0.0.1:$listenPort/docs" -ForegroundColor DarkGray
Write-Host "  ONEMLI: Paneli SADECE bu adresten acin; web klasorunu Live Server/http.server ile acmayin (API 404)." -ForegroundColor Yellow
Write-Host "  Dogrulama: http://127.0.0.1:$listenPort/__yt_tr_ping -> JSON 'youtube-tr-ceviri-backend' yazmali." -ForegroundColor DarkGray
Write-Host "  Kod degisince: Ctrl+C, bat tekrar (reload varsayilan KAPALI - guvenilir)." -ForegroundColor DarkGray
Write-Host "  CMD ciktisi: her HTTP istegi + [job ...] satirlari; Ctrl+C ile durdur" -ForegroundColor DarkGray
Write-Host "  NOT: http://0.0.0.0:$listenPort tarayicida CALISMAZ (sadece sunucu baglanti adresi)." -ForegroundColor Yellow
Write-Host "  Sunucu hazir olunca varsayilan tarayici acilacak." -ForegroundColor DarkGray
Write-Host "  Durdurmak icin: Ctrl+C" -ForegroundColor DarkGray
Write-Host "========================================"  -ForegroundColor Cyan
Write-Host ""

# Port acilinca bir kez varsayilan tarayicida ac (ayri PS sureci = kullanici oturumunda guvenilir)
$waitBrowserScript = Join-Path $env:TEMP "yt-tr-wait-browser.ps1"
@'
param([int]$Port, [string]$Url)
for ($i = 0; $i -lt 240; $i++) {
  $tcp = $null
  try {
    $tcp = [System.Net.Sockets.TcpClient]::new()
    $tcp.Connect('127.0.0.1', $Port)
    if ($tcp.Connected) {
      $tcp.Close()
      Start-Process $Url
      exit 0
    }
  } catch { }
  finally {
    if ($null -ne $tcp) { try { $tcp.Close() } catch { } }
  }
  Start-Sleep -Seconds 1
}
'@ | Set-Content -LiteralPath $waitBrowserScript -Encoding UTF8

try {
    Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden",
        "-File", $waitBrowserScript,
        "-Port", $listenPort,
        "-Url", $browserUrl
    ) -ErrorAction Stop | Out-Null
} catch {
    Write-Host "UYARI: Tarayici otomatik acma baslatilamadi (devam ediliyor): $($_.Exception.Message)" -ForegroundColor Yellow
}

# Python aninda cokerse veya .ps1 cift tiklanirsa pencere kapanmasin diye her cikista duraklat
$pythonExitCode = 0
try {
    & $py main.py
    if ($null -ne $LASTEXITCODE) { $pythonExitCode = $LASTEXITCODE }
} catch {
    Write-Host ""
    Write-Host "HATA (PowerShell): $($_.Exception.Message)" -ForegroundColor Red
    $pythonExitCode = 1
} finally {
    Write-Host ""
    Write-Host "--- Sunucu sureci bitti (Python cikis kodu: $pythonExitCode) ---" -ForegroundColor DarkYellow
    if ($pythonExitCode -ne 0) {
        Write-Host "Yukarida kirmizi/traceback var mi bakin (port, ffmpeg, modul eksigi)." -ForegroundColor Yellow
    }
    Write-Host "Pencereyi KAPATMADAN ONCE asagida Enter basin (log okumak icin)." -ForegroundColor Cyan
    try {
        Read-Host "Enter"
    } catch {
        Start-Sleep -Seconds 45
    }
}

exit $pythonExitCode
