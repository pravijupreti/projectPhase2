# modules/Jupyter/JupyterContainer.psm1
# Jupyter container management - reconfigure instead of delete

function Get-JupyterContainer {
    param(
        [string]$ContainerName,
        [string]$WorkspacePath,
        [int]$Port
    )
    
    $existing = docker ps -a --format "{{.Names}}" 2>$null
    
    if ($existing -contains $ContainerName) {
        # Get current volume mount
        $currentMount = docker inspect $ContainerName --format '{{range .Mounts}}{{.Source}}{{end}}' 2>$null
        
        # Get current port mapping
        $currentPort = docker inspect $ContainerName --format '{{range $p, $conf := .NetworkSettings.Ports}}{{$p}}{{end}}' 2>$null
        $currentPort = $currentPort -replace "/tcp", ""
        
        # Check if workspace changed - this requires recreation
        if ($currentMount -and $currentMount -ne $WorkspacePath) {
            Write-Host "Workspace changed: $currentMount -> $WorkspacePath" -ForegroundColor Yellow
            Write-Host "Container needs to be recreated for new workspace mount" -ForegroundColor Yellow
            return $false
        }
        
        # Check if port changed - we can reconfigure without deleting
        $portChanged = $false
        if ($currentPort -and [int]$currentPort -ne $Port) {
            Write-Host "Port changed: $currentPort -> $Port" -ForegroundColor Yellow
            $portChanged = $true
        }
        
        # Stop container if running
        $running = docker ps --format "{{.Names}}" 2>$null
        if ($running -contains $ContainerName) {
            Write-Host "Stopping container..." -ForegroundColor Yellow
            docker stop $ContainerName 2>&1 | Out-Null
            Start-Sleep -Seconds 2
        }
        
        # If port changed, reconfigure the container
        if ($portChanged) {
            Write-Host "Reconfiguring container with new port: $Port" -ForegroundColor Yellow
            $reconfigured = Reconfigure-ContainerPort -ContainerName $ContainerName -NewPort $Port
            if (-not $reconfigured) {
                Write-Host "Failed to reconfigure port, will recreate container" -ForegroundColor Red
                docker rm $ContainerName 2>&1 | Out-Null
                return $false
            }
        }
        
        # Start the container
        Write-Host "Starting container..." -ForegroundColor Yellow
        docker start $ContainerName 2>&1 | Out-Null
        Start-Sleep -Seconds 2
        
        return $true
    }
    else {
        return $false
    }
}

function Reconfigure-ContainerPort {
    param(
        [string]$ContainerName,
        [int]$NewPort
    )
    
    try {
        # Get container details
        $container = docker inspect $ContainerName | ConvertFrom-Json
        
        # Get the existing image and mounts
        $image = $container.Image
        $mounts = $container.Mounts
        $workingDir = $container.Config.WorkingDir
        $envVars = $container.Config.Env
        
        # Build new run command with updated port
        $gpuFlag = if ($container.HostConfig.DeviceRequests) { "--gpus all" } else { "" }
        
        # Extract volume mounts
        $volumeMounts = @()
        foreach ($mount in $mounts) {
            $volumeMounts += "-v ${mount.Source}:${mount.Destination}"
        }
        
        # Remove old container
        docker rm $ContainerName 2>&1 | Out-Null
        
        # Create new container with updated port
        $dockerCmd = "docker run -d $gpuFlag -p ${NewPort}:8888 $($volumeMounts -join ' ') -w $workingDir --name $ContainerName --restart unless-stopped $image jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser --allow-root --NotebookApp.token='' --NotebookApp.password=''"
        
        Write-Host "Recreating container with new port..." -ForegroundColor Gray
        $result = Invoke-Expression $dockerCmd 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Container reconfigured successfully" -ForegroundColor Green
            return $true
        }
        else {
            Write-Host "Failed to reconfigure: $result" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "Error reconfiguring container: $_" -ForegroundColor Red
        return $false
    }
}

function New-JupyterContainer {
    param(
        [string]$ContainerName,
        [bool]$HasGPU,
        [int]$Port = 8888,
        [string]$WorkspacePath
    )
    
    # Check if container exists and remove it if needed
    $existing = docker ps -a --format "{{.Names}}" 2>$null
    if ($existing -contains $ContainerName) {
        Write-Host "Removing existing container: $ContainerName" -ForegroundColor Yellow
        docker stop $ContainerName 2>&1 | Out-Null
        docker rm $ContainerName 2>&1 | Out-Null
        Start-Sleep -Seconds 2
    }
    
    # Determine image based on GPU
    if ($HasGPU) {
        $image = "tensorflow/tensorflow:2.15.0-gpu-jupyter"
        $gpuFlag = "--gpus all"
    }
    else {
        $image = "tensorflow/tensorflow:2.15.0-jupyter"
        $gpuFlag = ""
    }
    
    # Pull image
    Write-Host "Pulling Docker image: $image" -ForegroundColor Yellow
    $pullResult = Pull-DockerImage $image
    if (-not $pullResult) {
        Write-Host "Failed to pull Docker image" -ForegroundColor Red
        return @{ Success = $false; Port = $Port }
    }
    
    # Normalize path for Docker
    $normalizedPath = Normalize-PathForDocker -Path $WorkspacePath
    
    # Create container
    Write-Host "Creating container with workspace: $WorkspacePath" -ForegroundColor Yellow
    
    $dockerCmd = "docker run -d $gpuFlag -p ${Port}:8888 -v ${normalizedPath}:/tf/notebooks -w /tf/notebooks --name $ContainerName --restart unless-stopped $image jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser --allow-root --NotebookApp.token='' --NotebookApp.password=''"
    
    try {
        $result = Invoke-Expression $dockerCmd 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Container created successfully: $ContainerName" -ForegroundColor Green
            return @{ Success = $true; Port = $Port }
        }
        else {
            Write-Host "Container creation failed: $result" -ForegroundColor Red
            return @{ Success = $false; Port = $Port }
        }
    }
    catch {
        Write-Host "Container creation error: $_" -ForegroundColor Red
        return @{ Success = $false; Port = $Port }
    }
}

Export-ModuleMember -Function Get-JupyterContainer, New-JupyterContainer, Reconfigure-ContainerPort