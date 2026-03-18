# save as fix_docker.ps1
Write-Host "=" * 50
Write-Host "DOCKER FIX SCRIPT"
Write-Host "=" * 50

# Step 1: Kill all Docker processes
Write-Host "`nStep 1: Stopping all Docker processes..."
$dockerProcesses = Get-Process -Name "Docker Desktop", "dockerd", "com.docker.service" -ErrorAction SilentlyContinue
if ($dockerProcesses) {
    $dockerProcesses | ForEach-Object {
        Write-Host "  Stopping $_ (PID: $($_.Id))"
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "  All Docker processes stopped"
} else {
    Write-Host "  No Docker processes found"
}

# Step 2: Clean up Docker resources
Write-Host "`nStep 2: Cleaning up Docker resources..."
$dockerDir = "$env:APPDATA\Docker"
if (Test-Path $dockerDir) {
    Write-Host "  Note: Docker config files exist at: $dockerDir"
}

# Step 3: Restart Docker Desktop
Write-Host "`nStep 3: Starting Docker Desktop fresh..."
$dockerExe = "${env:ProgramFiles}\Docker\Docker\Docker Desktop.exe"
if (Test-Path $dockerExe) {
    Write-Host "  Launching Docker Desktop from: $dockerExe"
    Start-Process $dockerExe
    
    Write-Host "  Waiting 30 seconds for Docker to initialize..."
    Start-Sleep -Seconds 30
    
    # Step 4: Test Docker
    Write-Host "`nStep 4: Testing Docker..."
    $maxRetries = 10
    for ($i = 1; $i -le $maxRetries; $i++) {
        Write-Host "  Attempt $i/$maxRetries - Testing Docker connection..."
        try {
            $result = docker info 2>$null
            if ($result) {
                Write-Host "  ✅ Docker is working!"
                docker version
                break
            }
        } catch {
            Write-Host "  ⚠ Docker not ready yet..."
        }
        Start-Sleep -Seconds 3
    }
} else {
    Write-Host "  Error: Docker Desktop executable not found at: $dockerExe"
}

Write-Host "`n" + ("=" * 50)
Write-Host "Fix script completed"
Write-Host ("=" * 50)