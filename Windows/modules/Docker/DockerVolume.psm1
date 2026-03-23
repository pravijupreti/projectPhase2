# modules/Docker/DockerVolume.psm1
# Dynamic Docker volume management

function Get-DockerVolumeMount {
    param(
        [string]$HostPath,
        [string]$ContainerPath = "/tf/notebooks"
    )
    
    $normalizedPath = Normalize-PathForDocker -Path $HostPath
    return "-v ${normalizedPath}:${ContainerPath}"
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

function Get-WorkspaceMount {
    $workspace = Get-WorkspacePath
    return Get-DockerVolumeMount -HostPath $workspace
}

function Test-WorkspaceWritable {
    param([string]$Path)
    
    $testFile = Join-Path $Path ".jupyter_test_write.tmp"
    try {
        "test" | Out-File $testFile -ErrorAction Stop
        Remove-Item $testFile -Force
        return $true
    }
    catch {
        return $false
    }
}

function Get-WorkspaceInfo {
    $workspace = Get-WorkspacePath
    $exists = Test-Path $workspace
    $writable = if ($exists) { Test-WorkspaceWritable -Path $workspace } else { $false }
    $size = if ($exists) { 
        (Get-ChildItem $workspace -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum 
    } else { 0 }
    
    $sizeMB = [math]::Round($size / 1MB, 2)
    $notebookCount = if ($exists) { (Get-ChildItem $workspace -Filter "*.ipynb" -Recurse -ErrorAction SilentlyContinue).Count } else { 0 }
    
    $info = @{
        Path = $workspace
        Exists = $exists
        Writable = $writable
        SizeMB = $sizeMB
        NotebookCount = $notebookCount
    }
    
    return $info
}

function Show-WorkspaceInfo {
    $info = Get-WorkspaceInfo
    
    Write-Host ""
    Write-Host "Workspace Information:" -ForegroundColor Cyan
    Write-Host "  Path: $($info.Path)" -ForegroundColor White
    
    if ($info.Exists) {
        Write-Host "  Exists: Yes" -ForegroundColor Green
    } else {
        Write-Host "  Exists: No" -ForegroundColor Red
    }
    
    if ($info.Writable) {
        Write-Host "  Writable: Yes" -ForegroundColor Green
    } else {
        Write-Host "  Writable: No" -ForegroundColor Red
    }
    
    Write-Host "  Size: $($info.SizeMB) MB" -ForegroundColor White
    Write-Host "  Notebooks: $($info.NotebookCount)" -ForegroundColor White
}

Export-ModuleMember -Function Get-DockerVolumeMount, Normalize-PathForDocker, Get-WorkspaceMount, Test-WorkspaceWritable, Get-WorkspaceInfo, Show-WorkspaceInfo