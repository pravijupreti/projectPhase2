#!/usr/bin/env pwsh
# Windows/jupyter_notebook.ps1
# Main entry with Docker daemon check

# Disable strict mode for this script to avoid variable initialization errors
# Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

# Suppress warnings
$WarningPreference = "SilentlyContinue"

# Get paths
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$modulePath = Join-Path $scriptPath "modules"

# Import modules
Import-Module (Join-Path $modulePath "Core/WorkspaceManager.psm1") -Force -WarningAction SilentlyContinue
Import-Module (Join-Path $modulePath "Docker/DockerDetection.psm1") -Force -WarningAction SilentlyContinue
Import-Module (Join-Path $modulePath "Docker/DockerManagement.psm1") -Force -WarningAction SilentlyContinue

# ==================== DOCKER DAEMON CHECK FUNCTION ====================
function Test-DockerDaemonResponding {
    try {
        docker version --format '{{.Server.Version}}' 2>$null > $null
        return ($LASTEXITCODE -eq 0)
    }
    catch {
        return $false
    }
}

function Get-DockerVersion {
    try {
        $ver = docker version --format '{{.Server.Version}}' 2>$null
        if ($LASTEXITCODE -eq 0 -and $ver) {
            return $ver
        }
    }
    catch {
        return $null
    }
    return $null
}

function Start-DockerDesktop {
    $dockerPaths = @(
        "C:\Program Files\Docker\Docker\Docker Desktop.exe",
        "$env:LOCALAPPDATA\Docker\Docker Desktop.exe"
    )
    
    $dockerExe = $null
    foreach ($path in $dockerPaths) {
        if (Test-Path $path) {
            $dockerExe = $path
            break
        }
    }
    
    if (-not $dockerExe) {
        Write-Host "❌ Docker Desktop not found!" -ForegroundColor Red
        Write-Host "   Please install Docker Desktop from: https://www.docker.com/products/docker-desktop/" -ForegroundColor Yellow
        return $false
    }
    
    Write-Host "🚀 Starting Docker Desktop..." -ForegroundColor Yellow
    Start-Process $dockerExe
    return $true
}

function Ensure-DockerRunning {
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor Cyan
    Write-Host "DOCKER DAEMON CHECK" -ForegroundColor Cyan
    Write-Host ("=" * 60) -ForegroundColor Cyan
    
    # Step 1: Check if Docker daemon is responding
    Write-Host "`n📡 Checking if Docker daemon is responding..." -ForegroundColor Yellow
    
    $isResponding = Test-DockerDaemonResponding
    
    if ($isResponding) {
        $dockerVer = Get-DockerVersion
        if ($dockerVer) {
            Write-Host "✅ Docker daemon is responding (Version: $dockerVer)" -ForegroundColor Green
        } else {
            Write-Host "✅ Docker daemon is responding" -ForegroundColor Green
        }
        return $true
    }
    
    Write-Host "⚠️ Docker daemon is NOT responding" -ForegroundColor Red
    
    # Step 2: Check if Docker is installed
    $dockerInstalled = Test-DockerInstalled
    $dockerDesktop = Test-DockerDesktopInstalled
    
    if (-not $dockerInstalled -and -not $dockerDesktop) {
        Write-Host "❌ Docker is not installed!" -ForegroundColor Red
        Write-Host "   Please install Docker Desktop from: https://www.docker.com/products/docker-desktop/" -ForegroundColor Yellow
        return $false
    }
    
    # Step 3: Attempt to start Docker Desktop
    Write-Host "`n🔧 Attempting to start Docker Desktop..." -ForegroundColor Yellow
    
    $started = Start-DockerDesktop
    if (-not $started) {
        return $false
    }
    
    # Step 4: Wait for Docker to be ready (up to 30 seconds)
    Write-Host "⏳ Waiting for Docker daemon to start (max 30 seconds)..." -ForegroundColor Yellow
    
    for ($i = 1; $i -le 30; $i++) {
        Start-Sleep -Seconds 1
        Write-Host "   ... $i seconds" -NoNewline
        if ($i -eq 30) { Write-Host "" }
        else { Write-Host "`r" }
        
        if (Test-DockerDaemonResponding) {
            $dockerVer = Get-DockerVersion
            Write-Host "`n✅ Docker daemon is now responding" -ForegroundColor Green
            if ($dockerVer) {
                Write-Host "   Version: $dockerVer" -ForegroundColor Gray
            }
            return $true
        }
    }
    
    Write-Host "❌ Docker daemon failed to start after 30 seconds" -ForegroundColor Red
    Write-Host "   Please start Docker Desktop manually and try again." -ForegroundColor Yellow
    return $false
}

# ==================== MAIN EXECUTION ====================
# Initialize workspace (reads config silently)
Initialize-WorkspaceManager

# Detect OS
$osInfo = Get-CimInstance -ClassName Win32_OperatingSystem
$osName = $osInfo.Caption

if (-not ($osName -match "Windows")) {
    Write-Host "ERROR: This script is designed for Windows only" -ForegroundColor Red
    exit 1
}

# ENSURE DOCKER IS RUNNING - THIS IS CRITICAL
$dockerReady = Ensure-DockerRunning

if (-not $dockerReady) {
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor Red
    Write-Host "ERROR: DOCKER IS NOT RUNNING" -ForegroundColor Red
    Write-Host ("=" * 60) -ForegroundColor Red
    Write-Host ""
    Write-Host "Please start Docker Desktop manually and then run this script again." -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

# Launch Jupyter only if Docker is ready
Write-Host ""
Write-Host ("=" * 60) -ForegroundColor Green
Write-Host "DOCKER IS READY - LAUNCHING JUPYTER" -ForegroundColor Green
Write-Host ("=" * 60) -ForegroundColor Green

$launcher = Join-Path $scriptPath "launch_jupyter_gpu.ps1"

if (Test-Path $launcher) {
    & $launcher
}
else {
    Write-Host "ERROR: launch_jupyter_gpu.ps1 not found at: $launcher" -ForegroundColor Red
    exit 1
}