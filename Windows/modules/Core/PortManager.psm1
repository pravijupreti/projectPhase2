# modules/Core/PortManager.psm1
# Port management and safety functions

function Test-PortAvailable {
    param([int]$Port)
    
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $tcpClient.Connect("127.0.0.1", $Port)
        $tcpClient.Close()
        return $false
    }
    catch {
        return $true
    }
}

function Get-WindowsProcessUsingPort {
    param([int]$Port)
    
    $processes = @()
    try {
        $netstat = netstat -ano | Select-String ":$Port "
        
        foreach ($line in $netstat) {
            if ($line -match "LISTENING") {
                $parts = $line -split "\s+"
                $pid = $parts[-1]
                
                try {
                    $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
                    if ($process) {
                        $processes += @{
                            PID = $pid
                            Name = $process.ProcessName
                        }
                    }
                    else {
                        $processes += @{
                            PID = $pid
                            Name = "Unknown"
                        }
                    }
                }
                catch {
                    $processes += @{
                        PID = $pid
                        Name = "Unknown"
                    }
                }
            }
        }
    }
    catch {
        # Ignore errors
    }
    
    return $processes
}

function Get-DockerContainerUsingPort {
    param([int]$Port)
    
    $containers = @()
    try {
        $allContainers = docker ps -a --format "{{.Names}}\t{{.Status}}\t{{.Ports}}" 2>$null
        
        foreach ($container in $allContainers) {
            if ($container -match ":$Port" -or $container -match "->$Port/") {
                $parts = $container -split "`t"
                $status = if ($parts[1] -match "Up") { "running" } else { "stopped" }
                
                $containers += @{
                    Name = $parts[0]
                    Status = $status
                    Ports = $parts[2]
                }
            }
        }
    }
    catch {
        # Docker might not be running, ignore
    }
    
    return $containers
}

function Test-PortSafe {
    param([int]$Port)
    
    if ($Port -lt 1024 -or $Port -gt 65535) {
        $suggested = Get-SuggestedPort
        return @{
            Safe = $false
            Message = "Port $Port is outside valid range (1024-65535)"
            SuggestedPort = $suggested
        }
    }
    
    $isAvailable = Test-PortAvailable -Port $Port
    
    if (-not $isAvailable) {
        $windowsProcesses = Get-WindowsProcessUsingPort -Port $Port
        $dockerContainers = Get-DockerContainerUsingPort -Port $Port
        
        $message = "Port $Port is already in use"
        
        foreach ($p in $windowsProcesses) {
            $message = "$message`n  - Windows: $($p.Name) (PID: $($p.PID))"
        }
        
        foreach ($c in $dockerContainers) {
            $message = "$message`n  - Docker: $($c.Name) ($($c.Status))"
        }
        
        $suggestedPort = Get-SuggestedPort -StartPort ($Port + 1)
        
        return @{
            Safe = $false
            Message = $message
            SuggestedPort = $suggestedPort
        }
    }
    
    return @{
        Safe = $true
        Message = "Port $Port is available"
        SuggestedPort = $null
    }
}

function Get-SuggestedPort {
    param(
        [int]$StartPort = 8888,
        [int]$MaxAttempts = 100
    )
    
    $port = $StartPort
    
    for ($i = 0; $i -lt $MaxAttempts; $i++) {
        if (Test-PortAvailable -Port $port) {
            return $port
        }
        $port++
    }
    
    return $StartPort + $MaxAttempts
}

function Get-PortInfo {
    param([int]$Port)
    
    $available = Test-PortAvailable -Port $Port
    $windowsProcesses = Get-WindowsProcessUsingPort -Port $Port
    $dockerContainers = Get-DockerContainerUsingPort -Port $Port
    $suggestedPort = $null
    
    if (-not $available) {
        $suggestedPort = Get-SuggestedPort -StartPort ($Port + 1)
    }
    
    return @{
        Port = $Port
        Available = $available
        WindowsProcesses = $windowsProcesses
        DockerContainers = $dockerContainers
        SuggestedPort = $suggestedPort
    }
}

function Show-PortInfo {
    param([int]$Port)
    
    $info = Get-PortInfo -Port $Port
    
    Write-Host ""
    Write-Host ("=" * 50) -ForegroundColor Cyan
    Write-Host "PORT INFORMATION" -ForegroundColor Cyan
    Write-Host ("=" * 50) -ForegroundColor Cyan
    Write-Host "Port: $($info.Port)" -ForegroundColor White
    
    if ($info.Available) {
        Write-Host "Status: AVAILABLE" -ForegroundColor Green
    }
    else {
        Write-Host "Status: IN USE" -ForegroundColor Red
        
        if ($info.WindowsProcesses.Count -gt 0) {
            Write-Host ""
            Write-Host "Windows Processes:" -ForegroundColor Yellow
            foreach ($p in $info.WindowsProcesses) {
                Write-Host "  - $($p.Name) (PID: $($p.PID))" -ForegroundColor Gray
            }
        }
        
        if ($info.DockerContainers.Count -gt 0) {
            Write-Host ""
            Write-Host "Docker Containers:" -ForegroundColor Yellow
            foreach ($c in $info.DockerContainers) {
                Write-Host "  - $($c.Name) ($($c.Status))" -ForegroundColor Gray
            }
        }
        
        Write-Host ""
        Write-Host "Suggested Port: $($info.SuggestedPort)" -ForegroundColor Green
    }
    Write-Host ("=" * 50) -ForegroundColor Cyan
}

function Cleanup-Port {
    param([int]$Port)
    
    Write-Host "Checking port $Port..." -ForegroundColor Yellow
    
    $windowsProcesses = Get-WindowsProcessUsingPort -Port $Port
    $dockerContainers = Get-DockerContainerUsingPort -Port $Port
    
    if ($windowsProcesses.Count -gt 0) {
        Write-Host "Windows processes using port $Port:" -ForegroundColor Yellow
        foreach ($p in $windowsProcesses) {
            Write-Host "  - $($p.Name) (PID: $($p.PID))" -ForegroundColor Gray
        }
        Write-Host "Please close these applications manually." -ForegroundColor Yellow
    }
    
    if ($dockerContainers.Count -gt 0) {
        Write-Host "Docker containers using port $Port:" -ForegroundColor Yellow
        foreach ($c in $dockerContainers) {
            if ($c.Status -eq "running") {
                Write-Host "  Stopping container: $($c.Name)" -ForegroundColor Yellow
                docker stop $c.Name 2>&1 | Out-Null
                docker rm $c.Name 2>&1 | Out-Null
            }
        }
    }
    
    Start-Sleep -Seconds 2
    
    if (Test-PortAvailable -Port $Port) {
        Write-Host "Port $Port is now available" -ForegroundColor Green
        return $true
    }
    else {
        Write-Host "Port $Port is still in use" -ForegroundColor Red
        return $false
    }
}

Export-ModuleMember -Function Test-PortAvailable, Test-PortSafe, Get-SuggestedPort, 
                              Get-PortInfo, Show-PortInfo, Get-WindowsProcessUsingPort,
                              Get-DockerContainerUsingPort, Cleanup-Port