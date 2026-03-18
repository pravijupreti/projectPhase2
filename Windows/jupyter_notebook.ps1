#!/usr/bin/env pwsh
# jupyter_notebook.ps1
#Requires -Version 5.1

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# -----------------------------
# Detect OS
# -----------------------------
$osInfo = Get-CimInstance -ClassName Win32_OperatingSystem
$osName = $osInfo.Caption
Write-Host "OS: $osName"

if (-not ($osName -match "Windows")) {
    Write-Host "This script is designed for Windows only"
    exit 1
}

# -----------------------------
# Check Docker daemon
# -----------------------------
function Test-DockerDaemonResponding {
    docker version --format '{{.Server.Version}}' > $null 2>&1
    return ($LASTEXITCODE -eq 0)
}

# -----------------------------
# Check Docker CLI
# -----------------------------
function Test-DockerInstalled {
    return (Get-Command docker -ErrorAction SilentlyContinue) -ne $null
}

# -----------------------------
# Check Docker Desktop install
# -----------------------------
function Test-DockerDesktopInstalled {
    $paths = @(
        "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe",
        "$env:LOCALAPPDATA\Docker\Docker Desktop.exe"
    )
    foreach ($p in $paths) {
        if (Test-Path $p) { return $p }
    }
    return $null
}

# -----------------------------
# Stop Docker processes
# -----------------------------
function Stop-AllDockerProcesses {
    Write-Host "Stopping Docker processes..."
    $patterns = @("Docker Desktop","dockerd","vpnkit","com.docker*")
    foreach ($p in $patterns) {
        Get-Process -Name $p -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    }
    taskkill /F /IM "docker*.exe" > $null 2>&1
    taskkill /F /IM "com.docker*.exe" > $null 2>&1
    Start-Sleep 5
}

# -----------------------------
# Start Docker Desktop
# -----------------------------
function Start-DockerDesktop {
    $dockerExe = Test-DockerDesktopInstalled
    if (-not $dockerExe) {
        Write-Host "Docker Desktop not found"
        return $false
    }
    Write-Host "Starting Docker Desktop..."
    Start-Process $dockerExe
    Write-Host "Waiting for Docker daemon..."
    for ($i=1; $i -le 40; $i++) {
        Start-Sleep 3
        if (Test-DockerDaemonResponding) {
            Write-Host "Docker daemon is ready"
            return $true
        }
        if ($i % 5 -eq 0) {
            Write-Host "Still waiting... ($i / 40)"
        }
    }
    Write-Host "Docker daemon did not respond in time"
    return $false
}

# -----------------------------
# Restart Docker
# -----------------------------
function Restart-DockerDaemon {
    Write-Host "Restarting Docker..."
    Stop-AllDockerProcesses
    $started = Start-DockerDesktop
    return $started
}

# -----------------------------
# Pull Docker Image with Progress
# -----------------------------
function Pull-DockerImage([string]$image) {

    Write-Host "`n⬇ Pulling Docker image: $image"
    Write-Host ("=" * 60)

    try {

        # Run docker pull and stream output live
        docker pull $image 2>&1 | ForEach-Object {
            Write-Host $_
        }

        if ($LASTEXITCODE -eq 0) {
            Write-Host "`n✅ Image download completed"
            return $true
        }
        else {
            Write-Host "`n❌ Image pull failed"
            return $false
        }

    }
    catch {
        Write-Host "`n❌ Docker pull error: $_"
        return $false
    }
}

# -----------------------------
# MAIN
# -----------------------------
Write-Host ""
Write-Host ("=" * 40)
Write-Host " DOCKER CHECK"
Write-Host ("=" * 40)

$dockerInstalled = Test-DockerInstalled
$daemonRunning = Test-DockerDaemonResponding
$dockerDesktop = Test-DockerDesktopInstalled

Write-Host ""
Write-Host "Status:"
Write-Host "Docker CLI installed: $dockerInstalled"
Write-Host "Docker daemon running: $daemonRunning"
Write-Host "Docker Desktop installed: $dockerDesktop"

if ($daemonRunning) {
    $version = docker version --format '{{.Server.Version}}'
    Write-Host ""
    Write-Host "Docker already running (Version $version)"
    $dockerReady = $true
}
elseif ($dockerInstalled -or $dockerDesktop) {
    Write-Host ""
    Write-Host "Docker installed but daemon not running"
    Write-Host "Attempting automatic repair..."
    $dockerReady = Restart-DockerDaemon
}
else {
    Write-Host ""
    Write-Host "Docker is not installed. Download Docker Desktop from:"
    Write-Host "https://www.docker.com/products/docker-desktop/"
    exit 1
}

# -----------------------------
# If Docker ready
# -----------------------------
if ($dockerReady) {
    Write-Host ""
    Write-Host ("=" * 40)
    Write-Host " DOCKER READY"
    Write-Host ("=" * 40)

    Write-Host "`nTesting Docker..."
    docker run --rm hello-world

    $containerName = "jupyter-tf-gpu"
    $existing = docker ps -a --format "{{.Names}}"

    if ($existing -contains $containerName) {
        Write-Host "`nJupyter container exists"
        $running = docker ps --format "{{.Names}}"
        if ($running -notcontains $containerName) {
            Write-Host "Starting container..."
            docker start $containerName
        } else {
            Write-Host "Container already running"
        }
    }
    else {
        Write-Host "`nNo Jupyter container found"
        Write-Host "Pulling GPU-enabled Jupyter container..."
        $image = "tensorflow/tensorflow:latest-gpu-jupyter"
        $success = Pull-DockerImage $image
        if ($success) {
            Write-Host "`nCreating container..."
            $workspace = (Get-Location).Path
            docker run -d --name $containerName --gpus all -p 8888:8888 -v "${workspace}:/workspace" $image
        } else {
            Write-Host "`n❌ Failed to pull Docker image. Cannot create container."
            exit 1
        }
    }

    Write-Host ""
    Write-Host "Launching GPU Jupyter environment..."

    $launcher = "$PSScriptRoot\launch_jupyter_gpu.ps1"

    if (Test-Path $launcher) {
        & $launcher
    }
    else {
        Write-Host "❌ launch_jupyter_gpu.ps1 not found in:"
        Write-Host $launcher
    }
}
else {
    Write-Host ""
    Write-Host "Docker is not ready. Fix Docker manually and run again."
}

Write-Host ""
Write-Host ("=" * 40)
Write-Host " Setup complete!"
Write-Host ("=" * 40)