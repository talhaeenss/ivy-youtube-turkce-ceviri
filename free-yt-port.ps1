# Windows: port dinleyicilerini kapatmayi dener; yetkisiz sureclerde basarisiz olur (normal).
# Dot-source: . (Join-Path $PSScriptRoot "free-yt-port.ps1")

function Get-YtListeningPids {
    param([int]$Port)
    $conns = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
    @($conns | Select-Object -ExpandProperty OwningProcess -Unique | Where-Object { $_ -and $_ -gt 0 })
}

function Stop-YtPortListener {
    param([int]$ProcessId)
    $cmdLine = $null
    try {
        $w = Get-CimInstance -ClassName Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction SilentlyContinue
        if ($w) { $cmdLine = $w.CommandLine }
    } catch {}
    if ($cmdLine) {
        $short = if ($cmdLine.Length -gt 140) { $cmdLine.Substring(0, 140) + "..." } else { $cmdLine }
        Write-Host "    PID $ProcessId : $short" -ForegroundColor DarkGray
    } else {
        Write-Host "    PID $ProcessId : (isim/cmd alinamadi - genelde YONETICI/SYSTEM veya korumali surec)" -ForegroundColor Yellow
    }
    Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
    $tk = "taskkill /F /PID $ProcessId"
    $null = & cmd.exe /c $tk 2>&1
    $tkTree = "taskkill /F /T /PID $ProcessId"
    $null = & cmd.exe /c $tkTree 2>&1
}

function Write-YtPortKillFailureHelp {
    param([int]$Port, [int[]]$Pids)
    Write-Host ""
    Write-Host "--- NEDEN bu kadar denemede de kapanmiyor? ---" -ForegroundColor Yellow
    Write-Host 'O PID baska bir oturumda YONETICI / SYSTEM olarak calisiyor olabilir:' -ForegroundColor DarkGray
    Write-Host '  Bu durumda sizin aciginiz CMD/PowerShell onu sonlandiramaz (Windows guvenligi).' -ForegroundColor DarkGray
    Write-Host 'Ne yapilir: CMD veya Gorev Yoneticisi - sag tik - Yonetici olarak calistir; sonra taskkill veya Sonlandir.' -ForegroundColor DarkGray
    Write-Host 'Ya da otomatik baska bos port kullanilir (eklenti 8000 bekliyorsa tarayicidan yeni URL ile panel acin).' -ForegroundColor DarkGray
    Write-Host 'Hyper-V/WSL bazen port araligi ayirar: netsh interface ipv4 show excludedportrange protocol=tcp' -ForegroundColor DarkGray
    foreach ($id in ($Pids | Select-Object -Unique)) {
        Write-Host ""
        Write-Host ('tasklist (PID ' + $id + '):') -ForegroundColor Cyan
        $arg = 'PID eq ' + $id
        $out = & cmd.exe /c ('tasklist /FI "' + $arg + '" /FO LIST /V') 2>&1
        Write-Host ($out | Out-String).TrimEnd() -ForegroundColor DarkGray
    }
    Write-Host ""
    Write-Host ('netstat :' + $Port + '  dinleyen satirlar:') -ForegroundColor Cyan
    $all = & cmd.exe /c "netstat -ano" 2>&1
    $pat = ':' + $Port
    foreach ($line in $all) {
        if ($line -match [regex]::Escape($pat) -and $line -match 'LISTENING') {
            Write-Host $line -ForegroundColor DarkGray
        }
    }
    Write-Host ""
}

function Get-YtFirstFreeTcpPort {
    param(
        [int]$FromPort,
        [int]$ToPort
    )
    for ($p = $FromPort; $p -le $ToPort; $p++) {
        $listen = @(Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue)
        if ($listen.Count -eq 0) { return $p }
    }
    return $null
}

function Clear-YtListenPort {
    param(
        [int]$Port,
        [int]$MaxAttempts = 3,
        [int]$SleepSeconds = 2
    )
    $attempt = 0
    while ($true) {
        $pids = Get-YtListeningPids -Port $Port
        if ($pids.Count -eq 0) {
            if ($attempt -gt 0) {
                Write-Host ('>>> Port ' + $Port + ' bos (dinleyen yok).') -ForegroundColor Green
                Write-Host ""
            }
            return $true
        }
        $attempt++
        if ($attempt -gt $MaxAttempts) { break }
        $n = $pids.Count
        Write-Host ('>>> Port {0} kullanimda ({1} dinleyici). Kapatiliyor (deneme {2}/{3})...' -f $Port, $n, $attempt, $MaxAttempts) -ForegroundColor Yellow
        foreach ($procId in $pids) {
            Stop-YtPortListener -ProcessId $procId
        }
        Start-Sleep -Seconds $SleepSeconds
    }

    $still = Get-YtListeningPids -Port $Port
    if ($still.Count -gt 0) {
        Write-Host ""
        Write-Host ('!!! Port ' + $Port + ' hala dinleniyor. PID: ' + ($still -join ', ')) -ForegroundColor Red
        Write-YtPortKillFailureHelp -Port $Port -Pids $still
        return $false
    }
    return $true
}
