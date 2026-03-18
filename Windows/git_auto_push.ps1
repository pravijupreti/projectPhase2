# git_auto_push.ps1 - Complete Feature Version
$ErrorActionPreference = "Continue"

# ==================== CONFIGURATION ====================
$CONFIG_FILE = Join-Path $HOME ".jupyter_git_config.ps1"
$DEFAULT_BRANCH = "main"
$WORKSPACE_PATH = Get-Location
# ========================================================

function Write-Color {
    param([string]$Message, [ConsoleColor]$Color)
    Write-Host "[$([DateTime]::Now.ToString('HH:mm:ss'))] $Message" -ForegroundColor $Color
}

function Report-GitError {
    param([string]$Command, [string]$RawOutput)
    Write-Host "`n"
    Write-Color "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" -Color Red
    Write-Color "GIT ERROR DETECTED" -Color Red
    Write-Color "Command: $Command" -Color Yellow
    Write-Color "Exit Code: $LASTEXITCODE" -Color White
    Write-Color "----------------------------------------" -Color Gray
    Write-Color "RAW SYSTEM MESSAGE:" -Color Cyan
    Write-Host $RawOutput
    Write-Color "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!`n" -Color Red
}

function New-Config {
    Write-Color "No configuration found. Starting interactive setup..." -Color Yellow
    $repo = Read-Host "Enter GitHub repository URL"
    $branch = Read-Host "Enter branch name (default: main)"
    $global:GLOBAL_GITHUB_REPO = $repo
    $global:GLOBAL_CURRENT_BRANCH = if ([string]::IsNullOrWhiteSpace($branch)) { "main" } else { $branch }
    
    $configLines = @(
        "`$GITHUB_REPO = '$GLOBAL_GITHUB_REPO'",
        "`$CURRENT_BRANCH = '$GLOBAL_CURRENT_BRANCH'"
    )
    $configLines | Out-File -FilePath $CONFIG_FILE -Encoding utf8 -Force
    Write-Color "Config saved to $CONFIG_FILE" -Color Green
}

function Load-Config {
    if (Test-Path $CONFIG_FILE) {
        try {
            # Dot-source to pull variables from the config file
            . $CONFIG_FILE
            $global:GLOBAL_GITHUB_REPO = $GITHUB_REPO
            $global:GLOBAL_CURRENT_BRANCH = if ([string]::IsNullOrWhiteSpace($CURRENT_BRANCH)) { $DEFAULT_BRANCH } else { $CURRENT_BRANCH }
            Write-Color "Config loaded: $global:GLOBAL_GITHUB_REPO" -Color Green
        } catch {
            Write-Color "Config corrupted. Re-running setup..." -Color Yellow
            New-Config
        }
    } else {
        New-Config
    }
}

function Execute-Git {
    param([string]$GitParams)
    # Redirect stderr to stdout so we can capture everything in $result
    $fullCommand = "git $GitParams 2>&1"
    $result = Invoke-Expression $fullCommand
    
    if ($LASTEXITCODE -ne 0) {
        Report-GitError -Command "git $GitParams" -RawOutput ($result -join "`n")
        return $null
    }
    return $result
}

function Main {
    # 0. Context & Docker Prep
    Set-Location $WORKSPACE_PATH
    Write-Color "Starting Git Process in: $($WORKSPACE_PATH.Path)" -Color Cyan
    
    # Fix Docker 'Ownership' issues (Safe Directory)
    $safeDir = $WORKSPACE_PATH.Path.Replace('\', '/')
    git config --global --add safe.directory $safeDir 2>&1 | Out-Null

    # 1. Configuration
    Load-Config

    # 2. Repo Initialization
    if (-not (Test-Path ".git")) {
        Write-Color "No .git found. Initializing new repository..." -Color Yellow
        $null = Execute-Git "init"
    }

    # 3. Identity Check
    if ([string]::IsNullOrEmpty((git config user.name))) {
        git config user.email "jupyter@auto.push"
        git config user.name "Jupyter User"
    }

    # 4. Handle Local Changes
    Write-Color "Checking for changes..." -Color Yellow
    $status = git status --porcelain 2>&1
    
    if (-not [string]::IsNullOrWhiteSpace($status)) {
        Write-Color "Changes found. Staging and committing..." -Color Green
        $null = Execute-Git "add ."
        $null = Execute-Git "commit -m 'Auto-backup-$(Get-Date -Format 'HH-mm-ss')'"
    } else {
        Write-Color "No new changes to commit." -Color Gray
    }

    # 5. GitHub Synchronization
    if (-not [string]::IsNullOrEmpty($global:GLOBAL_GITHUB_REPO)) {
        Write-Color "Syncing with GitHub..." -Color Magenta
        
        # Reset remote to match the current UI/Config
        git remote remove origin 2>&1 | Out-Null
        $null = Execute-Git "remote add origin $global:GLOBAL_GITHUB_REPO"
        
        Write-Color "Pushing to $global:GLOBAL_CURRENT_BRANCH --force" -Color Yellow
        # We push specifically using local:remote format to be explicit
        $pushResult = Execute-Git "push origin $($global:GLOBAL_CURRENT_BRANCH):$($global:GLOBAL_CURRENT_BRANCH) --force"
        
        if ($null -ne $pushResult) {
            Write-Color "SUCCESS: Project backed up to GitHub" -Color Green
        }
    }
}

Main