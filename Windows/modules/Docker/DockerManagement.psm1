# modules/Docker/DockerManagement.psm1
# Docker start/stop/restart functions

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

function Restart-DockerDaemon {
    Write-Host "Restarting Docker..."
    Stop-AllDockerProcesses
    $started = Start-DockerDesktop
    return $started
}

Export-ModuleMember -Function Stop-AllDockerProcesses, Start-DockerDesktop, Restart-DockerDaemon