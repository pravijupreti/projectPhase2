# modules/Core/WorkspaceManager.psm1
# Manages user workspace directory for Jupyter notebooks

$script:ConfigFile = "$env:USERPROFILE\.jupyter_workspace_config.json"
$script:Config = $null

function Initialize-WorkspaceManager {
    Load-WorkspaceConfig
}

function Load-WorkspaceConfig {
    if (Test-Path $script:ConfigFile) {
        try {
            $script:Config = Get-Content $script:ConfigFile | ConvertFrom-Json
            Write-Host "Loaded workspace config from: $script:ConfigFile" -ForegroundColor Green
        }
        catch {
            Write-Host "Failed to load config, using defaults" -ForegroundColor Yellow
            $script:Config = @{}
        }
    }
    else {
        $script:Config = @{}
        Write-Host "No existing workspace config, will create on first save" -ForegroundColor Gray
    }
}

function Save-WorkspaceConfig {
    $script:Config | ConvertTo-Json | Set-Content $script:ConfigFile
    Write-Host "Workspace config saved to: $script:ConfigFile" -ForegroundColor Green
}

function Get-WorkspacePath {
    if ($script:Config.workspace_path -and (Test-Path $script:Config.workspace_path)) {
        return $script:Config.workspace_path
    }
    elseif ($script:Config.workspace_path) {
        Write-Host "Saved workspace path not found: $($script:Config.workspace_path)" -ForegroundColor Yellow
        Write-Host "Using current directory as fallback." -ForegroundColor Gray
        return (Get-Location).Path
    }
    else {
        $defaultPath = Join-Path $env:USERPROFILE "Documents\JupyterWorkspace"
        if (-not (Test-Path $defaultPath)) {
            New-Item -ItemType Directory -Path $defaultPath -Force | Out-Null
        }
        return $defaultPath
    }
}

function Set-WorkspacePath {
    param(
        [string]$Path,
        [switch]$CreateIfNotExist
    )
    
    if (-not $Path) {
        Write-Host "No path provided" -ForegroundColor Red
        return $false
    }
    
    $expandedPath = [Environment]::ExpandEnvironmentVariables($Path)
    
    if (-not (Test-Path $expandedPath)) {
        if ($CreateIfNotExist) {
            Write-Host "Creating workspace directory: $expandedPath" -ForegroundColor Yellow
            try {
                New-Item -ItemType Directory -Path $expandedPath -Force | Out-Null
                Write-Host "Workspace directory created" -ForegroundColor Green
            }
            catch {
                Write-Host "Failed to create directory: $_" -ForegroundColor Red
                return $false
            }
        }
        else {
            Write-Host "Path does not exist: $expandedPath" -ForegroundColor Red
            Write-Host "Use -CreateIfNotExist to create it automatically" -ForegroundColor Gray
            return $false
        }
    }
    
    $script:Config.workspace_path = $expandedPath
    Save-WorkspaceConfig
    
    Write-Host "Workspace path set to: $expandedPath" -ForegroundColor Green
    return $true
}

function Show-WorkspaceMenu {
    param(
        [string]$CurrentWorkspace,
        [bool]$AllowChange = $true
    )
    
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor Cyan
    Write-Host "JUPYTER WORKSPACE CONFIGURATION" -ForegroundColor Cyan
    Write-Host ("=" * 60) -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Current Workspace: $CurrentWorkspace" -ForegroundColor White
    Write-Host ""
    
    if ($AllowChange) {
        Write-Host "Options:" -ForegroundColor Yellow
        Write-Host "  1. Keep current workspace" -ForegroundColor White
        Write-Host "  2. Change workspace directory" -ForegroundColor White
        Write-Host "  3. Create new workspace directory" -ForegroundColor White
        Write-Host ""
        
        $choice = Read-Host "Select option (1-3)"
        
        switch ($choice) {
            "2" {
                $newPath = Read-Host "Enter new workspace path (e.g., D:\MyJupyterNotebooks)"
                if ($newPath) {
                    Set-WorkspacePath -Path $newPath -CreateIfNotExist
                    return Get-WorkspacePath
                }
            }
            "3" {
                $newPath = Read-Host "Enter path for new workspace"
                if ($newPath) {
                    Set-WorkspacePath -Path $newPath -CreateIfNotExist
                    return Get-WorkspacePath
                }
            }
            default {
                Write-Host "Keeping current workspace" -ForegroundColor Green
            }
        }
    }
    
    return $CurrentWorkspace
}

Export-ModuleMember -Function Initialize-WorkspaceManager, Get-WorkspacePath, Set-WorkspacePath, Show-WorkspaceMenu, Save-WorkspaceConfig