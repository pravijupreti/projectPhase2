# save as fix_docker_daemon.ps1 - RUN AS ADMINISTRATOR
Write-Host "=" * 60
Write-Host "DOCKER DAEMON FIX - CLEAN SLATE APPROACH"
Write-Host "=" * 60

# 1. Kill all Docker processes
Write-Host "`nStep 1: Killing all Docker processes..."
Get-Process -Name "Docker Desktop", "dockerd", "com.docker.service" -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 5

# 2. Stop Docker service
Write-Host "`nStep 2: Stopping Docker service..."
Stop-Service -Name "com.docker.service" -Force -ErrorAction SilentlyContinue

# 3. THIS IS THE KEY STEP - Reset WSL2 distributions
Write-Host "`nStep 3: Resetting corrupted WSL2 distributions..." -ForegroundColor Yellow
Write-Host "This will remove Docker's internal WSL distros (they will be recreated automatically)"

# Check if distributions exist
$distros = wsl -l -v | Select-String "docker-desktop"
if ($distros) {
    Write-Host "Unregistering docker-desktop..."
    wsl --unregister docker-desktop 2>$null
    
    Write-Host "Unregistering docker-desktop-data..."
    wsl --unregister docker-desktop-data 2>$null
    
    Write-Host "WSL distributions reset complete" -ForegroundColor Green
} else {
    Write-Host "No Docker WSL distributions found"
}

# 4. Clean Docker config (optional but often helps)
Write-Host "`nStep 4: Cleaning Docker config (backing up first)..."
$dockerConfig = "$env:APPDATA\Docker"
if (Test-Path $dockerConfig) {
    $backupDir = "$env:APPDATA\Docker_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    Write-Host "Backing up config to: $backupDir"
    Copy-Item -Path $dockerConfig -Destination $backupDir -Recurse
    
    # Don't delete everything - just the problematic files
    Write-Host "Cleaning corrupted settings..."
    Remove-Item "$dockerConfig\settings.json" -ErrorAction SilentlyContinue
}

# 5. Ensure Hyper-V and WSL are properly enabled
Write-Host "`nStep 5: Ensuring virtualization features are enabled..."
dism /online /enable-feature /featurename:Microsoft-Hyper-V /all /norestart 2>$null
dism /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart 2>$null
wsl --update 2>$null

# 6. Fresh start
Write-Host "`nStep 6: Starting Docker Desktop fresh..."
$dockerExe = "${env:ProgramFiles}\Docker\Docker\Docker Desktop.exe"
if (Test-Path $dockerExe) {
    Start-Process $dockerExe
    
    Write-Host "Waiting 60 seconds for daemon to initialize..." -ForegroundColor Yellow
    for ($i = 1; $i -le 12; $i++) {
        Start-Sleep -Seconds 5
        Write-Host "  Still waiting... ($i of 12)"
        
        # Check if dockerd appears
        $dockerd = Get-Process -Name "dockerd" -ErrorAction SilentlyContinue
        if ($dockerd) {
            Write-Host "`nSUCCESS: dockerd process detected!" -ForegroundColor Green
            break
        }
    }
    
    # Final check
    Start-Sleep -Seconds 10
    try {
        $version = docker version 2>$null
        if ($version) {
            Write-Host "`n✅ Docker daemon is now RUNNING!" -ForegroundColor Green
            docker version --format '{{.Server.Version}}'
        }
    } catch {
        Write-Host "`n❌ Daemon still not responding"
    }
}

Write-Host "`n" + ("=" * 60)
Write-Host "Fix script completed"
Write-Host ("=" * 60)