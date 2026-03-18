#!/usr/bin/env pwsh
# launch_jupyter_gpu.ps1 (FINAL FIXED VERSION)

#Requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$PORT = 8888
Write-Host "Using port $PORT for Jupyter Notebook."

# ================= GPU CHECK =================
function Test-NvidiaGPU {
    try {
        $gpu = Get-WmiObject Win32_VideoController | Where-Object { $_.Name -like "*NVIDIA*" }
        if ($gpu) { return $true }

        $nvidia = Get-Command nvidia-smi -ErrorAction SilentlyContinue
        if ($nvidia) {
            $out = & nvidia-smi --query-gpu=name --format=csv,noheader 2>$null
            if ($out) { return $true }
        }
    } catch {}
    return $false
}

# ================= WAIT FOR JUPYTER =================
function Wait-ForJupyter {
    param([int]$Port)

    $tries = 60
    Write-Host "Waiting for Jupyter..." -NoNewline

    for ($i = 1; $i -le $tries; $i++) {
        try {
            $r = Invoke-WebRequest "http://localhost:$Port" -UseBasicParsing -TimeoutSec 2
            if ($r.StatusCode -eq 200 -or $r.StatusCode -eq 302) {
                Write-Host ""
                Write-Host "Jupyter Ready"
                return $true
            }
        } catch {}

        Write-Host "." -NoNewline
        Start-Sleep 1
    }

    Write-Host ""
    Write-Host "Jupyter not responding"
    return $false
}

# ================= OPEN BROWSER =================
function Open-Browser {
    param([string]$Url)

    Write-Host "Opening browser $Url"

    $process = Start-Process $Url -PassThru
    $process.Id | Out-File "$env:TEMP\jupyter_browser.pid"
}

# ================= MONITOR BROWSER =================
function Monitor-Browser {
    param([string]$Container)

    $pidfile = "$env:TEMP\jupyter_browser.pid"

    if (!(Test-Path $pidfile)) { return }

    $browserPid = [int](Get-Content $pidfile)

    Write-Host "Monitoring browser window..."

    while ($true) {
        Start-Sleep 2
        try {
            Get-Process -Id $browserPid -ErrorAction Stop > $null
        } catch {
            break
        }
    }

    Write-Host "Browser closed → triggering git push"

    $gitScript = Join-Path $PSScriptRoot "git_auto_push.ps1"

    if (Test-Path $gitScript) {
        Write-Host "Running git_auto_push.ps1..."

        try {
            # ✅ FIXED CALL (NO param error)
            powershell -ExecutionPolicy Bypass -File "$gitScript" "window_closed" 2>&1 | ForEach-Object {
                Write-Host $_
            }
            Write-Host "Git script finished"
        } catch {
            Write-Host "Git script ERROR:" -ForegroundColor Red
            Write-Host $_
        }
    } else {
        Write-Host "git_auto_push.ps1 not found!" -ForegroundColor Red
    }

    Remove-Item $pidfile -Force -ErrorAction SilentlyContinue
}

# ================= DOCKER SETUP =================
$hasGPU = Test-NvidiaGPU

if ($hasGPU) {

    Write-Host "NVIDIA GPU detected"

    $CONTAINER = "jupyter-tf-gpu"

    $existing = docker ps -a --format "{{.Names}}"
    if ($existing -contains $CONTAINER) {
        docker rm -f $CONTAINER | Out-Null
    }

    Write-Host "Pulling TensorFlow GPU image"
    docker pull tensorflow/tensorflow:2.15.0-gpu-jupyter

    docker run --gpus all -d `
        -p ${PORT}:8888 `
        -v "${PWD}:/tf/notebooks" `
        -w /tf/notebooks `
        --name $CONTAINER `
        --restart unless-stopped `
        tensorflow/tensorflow:2.15.0-gpu-jupyter `
        jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser --allow-root --NotebookApp.token='' --NotebookApp.password=''
}
else {

    Write-Host "No GPU detected → using CPU container"

    $CONTAINER = "jupyter-tf-cpu"

    $existing = docker ps -a --format "{{.Names}}"
    if ($existing -contains $CONTAINER) {
        docker rm -f $CONTAINER | Out-Null
    }

    Write-Host "Pulling TensorFlow CPU image"
    docker pull tensorflow/tensorflow:2.15.0-jupyter

    docker run -d `
        -p ${PORT}:8888 `
        -v "${PWD}:/tf/notebooks" `
        -w /tf/notebooks `
        --name $CONTAINER `
        --restart unless-stopped `
        tensorflow/tensorflow:2.15.0-jupyter `
        jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser --allow-root --NotebookApp.token='' --NotebookApp.password=''
}

# ================= START =================
if (Wait-ForJupyter -Port $PORT) {
    Open-Browser "http://localhost:$PORT/tree"
}

Write-Host ""
Write-Host "Container logs:"
docker logs $CONTAINER --tail 10

Monitor-Browser $CONTAINER

Write-Host ""
Write-Host "Session ended."
Write-Host "Container still running: docker ps"
Write-Host "Stop container: docker stop $CONTAINER"