#!/usr/bin/env pwsh
# Windows/launch_jupyter_gpu.ps1
# Complete fixed version with proper port detection

#Requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

# Suppress warnings
$WarningPreference = "SilentlyContinue"

# ==================== ROBUST PORT CHECKING FUNCTIONS ====================
function Test-PortAvailable {
    param([int]$Port)
    
    # Method 1: Check netstat for LISTENING ports
    $netstat = netstat -ano 2>$null | Select-String ":$Port "
    $listening = $netstat | Select-String "LISTENING"
    
    if ($listening) {
        return $false  # Port is in use
    }
    
    # Method 2: Try to create a TCP connection
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $tcpClient.Connect("127.0.0.1", $Port)
        $tcpClient.Close()
        return $false  # Port is in use (connection succeeded)
    }
    catch {
        # Connection failed, port is likely free
        return $true
    }
}

function Get-ProcessOnPort {
    param([int]$Port)
    
    $netstat = netstat -ano 2>$null | Select-String ":$Port " | Select-String "LISTENING"
    
    if ($netstat) {
        # Parse the output to get PID
        $line = $netstat.ToString()
        $parts = $line -split '\s+'
        $pid = $parts[-1]
        
        try {
            $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
            return @{
                PID = $pid
                Name = if ($process) { $process.ProcessName } else { "Unknown" }
                Path = if ($process -and $process.Path) { $process.Path } else { "Unknown" }
            }
        }
        catch {
            return @{ PID = $pid; Name = "Unknown"; Path = "Unknown" }
        }
    }
    return $null
}

function Find-NextAvailablePort {
    param(
        [int]$StartPort = 8888,
        [int]$MaxAttempts = 100
    )
    
    for ($i = 0; $i -lt $MaxAttempts; $i++) {
        $port = $StartPort + $i
        if (Test-PortAvailable -Port $port) {
            return $port
        }
    }
    return $null
}

function Show-PortStatus {
    param([int]$Port)
    
    $available = Test-PortAvailable -Port $Port
    if ($available) {
        Write-Host "Port $($Port): AVAILABLE" -ForegroundColor Green
        return $true
    }
    else {
        $process = Get-ProcessOnPort -Port $Port
        Write-Host "Port $($Port): IN USE by $($process.Name) (PID: $($process.PID))" -ForegroundColor Red
        return $false
    }
}

# ==================== LOAD CONFIGURATIONS ====================
function Load-WorkspaceConfig {
    $configFile = "$env:USERPROFILE\.jupyter_workspace_config.json"
    $defaultWorkspace = Join-Path $env:USERPROFILE "Documents\JupyterWorkspace"
    
    if (Test-Path $configFile) {
        try {
            $config = Get-Content $configFile | ConvertFrom-Json
            $workspace = $config.workspace_path
            if (Test-Path $workspace) {
                Write-Host "Loaded workspace: $($workspace)" -ForegroundColor Gray
                return $workspace
            }
            else {
                Write-Host "Saved workspace not found, using default" -ForegroundColor Yellow
                return $defaultWorkspace
            }
        }
        catch {
            Write-Host "Error loading workspace config, using default" -ForegroundColor Yellow
            return $defaultWorkspace
        }
    }
    else {
        Write-Host "No workspace config found, using default" -ForegroundColor Gray
        return $defaultWorkspace
    }
}

function Load-PortConfig {
    $configFile = "$env:USERPROFILE\.jupyter_port_config.json"
    $defaultPort = 8888
    
    if (Test-Path $configFile) {
        try {
            $config = Get-Content $configFile | ConvertFrom-Json
            $port = $config.port
            Write-Host "Loaded saved port: $($port)" -ForegroundColor Gray
            return $port
        }
        catch {
            Write-Host "Error loading port config, using default" -ForegroundColor Yellow
            return $defaultPort
        }
    }
    else {
        Write-Host "No port config found, using default" -ForegroundColor Gray
        return $defaultPort
    }
}

function Save-PortConfig {
    param([int]$Port)
    
    $configFile = "$env:USERPROFILE\.jupyter_port_config.json"
    $config = @{ port = $Port } | ConvertTo-Json
    $config | Set-Content $configFile
    Write-Host "Port configuration saved: $($Port)" -ForegroundColor Gray
}

# ==================== DOCKER FUNCTIONS ====================
function Test-DockerRunning {
    try {
        docker version --format '{{.Server.Version}}' 2>$null > $null
        return ($LASTEXITCODE -eq 0)
    }
    catch {
        return $false
    }
}

function Test-NvidiaGPU {
    try {
        $gpu = Get-WmiObject Win32_VideoController | Where-Object { $_.Name -like "*NVIDIA*" }
        if ($gpu) { return $true }
        
        $nvidia = Get-Command nvidia-smi -ErrorAction SilentlyContinue
        if ($nvidia) {
            $out = & nvidia-smi --query-gpu=name --format=csv,noheader 2>$null
            if ($out) { return $true }
        }
    }
    catch {}
    return $false
}

function Normalize-PathForDocker {
    param([string]$Path)
    $normalized = $Path -replace '\\', '/'
    if ($normalized -match '^([A-Za-z]):/') {
        $drive = $matches[1].ToLower()
        $normalized = "/$drive" + $normalized.Substring(2)
    }
    return $normalized
}

function Pull-DockerImage {
    param([string]$image)
    
    Write-Host "Pulling Docker image: $image" -ForegroundColor Yellow
    Write-Host ("=" * 60) -ForegroundColor Gray
    
    $result = docker pull $image 2>&1
    foreach ($line in $result) {
        Write-Host $line
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Image download completed" -ForegroundColor Green
        return $true
    }
    else {
        Write-Host "Image pull failed" -ForegroundColor Red
        return $false
    }
}

# ==================== CONTAINER MANAGEMENT ====================
function Manage-Container {
    param(
        [string]$ContainerName,
        [string]$WorkspacePath,
        [int]$Port,
        [bool]$HasGPU
    )
    
    $existing = docker ps -a --format "{{.Names}}" 2>$null
    
    if ($existing -contains $ContainerName) {
        Write-Host "Container exists: $ContainerName" -ForegroundColor Yellow
        
        # Get current configuration
        $currentMount = docker inspect $ContainerName --format '{{range .Mounts}}{{.Source}}{{end}}' 2>$null
        $currentPort = docker inspect $ContainerName --format '{{range $p, $conf := .NetworkSettings.Ports}}{{$p}}{{end}}' 2>$null
        $currentPort = $currentPort -replace "/tcp", ""
        
        $needsRecreate = $false
        
        if ($currentMount -and $currentMount -ne $WorkspacePath) {
            Write-Host "  Workspace changed: $($currentMount) -> $($WorkspacePath)" -ForegroundColor Yellow
            $needsRecreate = $true
        }
        
        if ($currentPort -and [int]$currentPort -ne $Port) {
            Write-Host "  Port changed: $($currentPort) -> $($Port)" -ForegroundColor Yellow
            $needsRecreate = $true
        }
        
        if ($needsRecreate) {
            Write-Host "Recreating container with new settings..." -ForegroundColor Yellow
            docker rm -f $ContainerName 2>&1 | Out-Null
            Start-Sleep -Seconds 2
            return $false
        }
        else {
            # Start if not running
            $running = docker ps --format "{{.Names}}" 2>$null
            if ($running -notcontains $ContainerName) {
                Write-Host "Starting existing container..." -ForegroundColor Yellow
                docker start $ContainerName 2>&1 | Out-Null
            } else {
                Write-Host "Container already running" -ForegroundColor Green
            }
            return $true
        }
    }
    
    return $false
}

function Create-Container {
    param(
        [string]$ContainerName,
        [string]$WorkspacePath,
        [int]$Port,
        [bool]$HasGPU
    )
    
    if ($HasGPU) {
        $image = "tensorflow/tensorflow:2.15.0-gpu-jupyter"
        $gpuFlag = "--gpus all"
        Write-Host "Creating GPU-enabled container..." -ForegroundColor Cyan
    }
    else {
        $image = "tensorflow/tensorflow:2.15.0-jupyter"
        $gpuFlag = ""
        Write-Host "Creating CPU container..." -ForegroundColor Cyan
    }
    
    Write-Host "  Image: $image" -ForegroundColor Gray
    Write-Host "  Port: ${Port}:8888" -ForegroundColor Gray
    Write-Host "  Workspace: $($WorkspacePath) -> /tf/notebooks" -ForegroundColor Gray
    
    # Pull image
    $pullResult = Pull-DockerImage $image
    if (-not $pullResult) {
        Write-Host "Failed to pull Docker image" -ForegroundColor Red
        return $false
    }
    
    # Normalize path
    $normalizedPath = Normalize-PathForDocker -Path $WorkspacePath
    
    # Create container
    Write-Host "Creating container..." -ForegroundColor Yellow
    $dockerCmd = "docker run -d $gpuFlag -p ${Port}:8888 -v ${normalizedPath}:/tf/notebooks -w /tf/notebooks --name $ContainerName --restart unless-stopped $image jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser --allow-root --NotebookApp.token='' --NotebookApp.password=''"
    
    try {
        $result = Invoke-Expression $dockerCmd 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Container created successfully: $ContainerName" -ForegroundColor Green
            return $true
        }
        else {
            Write-Host "Container creation failed: $result" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "Container creation error: $_" -ForegroundColor Red
        return $false
    }
}

# ==================== WAIT FOR JUPYTER ====================
function Wait-ForJupyter {
    param([int]$Port)
    
    Write-Host "Waiting for Jupyter on port $($Port)..." -ForegroundColor Yellow
    
    for ($i = 1; $i -le 60; $i++) {
        try {
            $response = Invoke-WebRequest "http://localhost:$($Port)" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200 -or $response.StatusCode -eq 302) {
                return $true
            }
        }
        catch {
            # Still waiting
        }
        
        if ($i % 10 -eq 0) {
            Write-Host "Still waiting... ($i seconds)" -ForegroundColor Gray
        }
        Start-Sleep -Seconds 1
    }
    
    return $false
}

# ==================== MAIN EXECUTION ====================
Write-Host ""
Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host "JUPYTER DOCKER LAUNCHER" -ForegroundColor Cyan
Write-Host ("=" * 60) -ForegroundColor Cyan

# Load configurations
$workspace = Load-WorkspaceConfig
$savedPort = Load-PortConfig

# Create workspace if it doesn't exist
if (-not (Test-Path $workspace)) {
    Write-Host "Creating workspace directory: $($workspace)" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $workspace -Force | Out-Null
}

# Check workspace writability
$testFile = Join-Path $workspace ".test_write.tmp"
try {
    "test" | Out-File $testFile -ErrorAction Stop
    Remove-Item $testFile -Force
    Write-Host "Workspace is writable: $($workspace)" -ForegroundColor Green
}
catch {
    Write-Host "ERROR: Workspace is not writable: $($workspace)" -ForegroundColor Red
    exit 1
}

# Port checking and selection
Write-Host ""
Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host "PORT CONFIGURATION" -ForegroundColor Cyan
Write-Host ("=" * 60) -ForegroundColor Cyan

Write-Host "Checking saved port $($savedPort)..." -ForegroundColor Gray
$portAvailable = Test-PortAvailable -Port $savedPort

if ($portAvailable) {
    Write-Host "Port $($savedPort) is AVAILABLE" -ForegroundColor Green
    $PORT = $savedPort
}
else {
    $processInfo = Get-ProcessOnPort -Port $savedPort
    Write-Host "Port $($savedPort) is IN USE by $($processInfo.Name) (PID: $($processInfo.PID))" -ForegroundColor Red
    
    Write-Host "Searching for next available port..." -ForegroundColor Yellow
    $PORT = Find-NextAvailablePort -StartPort ($savedPort + 1)
    
    if (-not $PORT) {
        Write-Host "ERROR: Could not find an available port" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Found available port: $($PORT)" -ForegroundColor Green
    Save-PortConfig -Port $PORT
}

# Check GPU
$hasGPU = Test-NvidiaGPU
if ($hasGPU) {
    Write-Host "GPU: NVIDIA GPU detected" -ForegroundColor Green
} else {
    Write-Host "GPU: No NVIDIA GPU detected (using CPU)" -ForegroundColor Yellow
}

# Container setup
Write-Host ""
Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host "CONTAINER SETUP" -ForegroundColor Cyan
Write-Host ("=" * 60) -ForegroundColor Cyan

$CONTAINER_NAME = "jupyter-tf-workspace"
$containerExists = Manage-Container -ContainerName $CONTAINER_NAME -WorkspacePath $workspace -Port $PORT -HasGPU $hasGPU

if (-not $containerExists) {
    $created = Create-Container -ContainerName $CONTAINER_NAME -WorkspacePath $workspace -Port $PORT -HasGPU $hasGPU
    if (-not $created) {
        Write-Host "ERROR: Failed to create container" -ForegroundColor Red
        exit 1
    }
}

# Wait for Jupyter
Write-Host ""
Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host "STARTING JUPYTER" -ForegroundColor Cyan
Write-Host ("=" * 60) -ForegroundColor Cyan

$jupyterReady = Wait-ForJupyter -Port $PORT

if ($jupyterReady) {
    # Open browser
    Start-Process "http://localhost:$($PORT)/tree"
    
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor Green
    Write-Host "JUPYTER NOTEBOOK RUNNING" -ForegroundColor Green
    Write-Host ("=" * 60) -ForegroundColor Green
    Write-Host "Workspace: $($workspace)" -ForegroundColor Cyan
    Write-Host "URL: http://localhost:$($PORT)/tree" -ForegroundColor Cyan
    Write-Host "Port: $($PORT)" -ForegroundColor Cyan
    Write-Host "Container: $($CONTAINER_NAME)" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Press Ctrl+C to stop the server." -ForegroundColor Yellow
    Write-Host ""
    
    # Keep script running
    try {
        while ($true) {
            Start-Sleep -Seconds 5
        }
    }
    catch {
        # Handle Ctrl+C
    }
    
    # Cleanup
    Write-Host "Stopping container..." -ForegroundColor Yellow
    docker stop $CONTAINER_NAME 2>&1 | Out-Null
    Write-Host "Container stopped." -ForegroundColor Green
}
else {
    Write-Host "ERROR: Jupyter failed to start on port $($PORT)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Container logs:" -ForegroundColor Yellow
    docker logs $CONTAINER_NAME --tail 20
    exit 1
}