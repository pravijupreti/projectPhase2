# git_auto_push.ps1 - Complete Feature Version
$ErrorActionPreference = "Continue"

# ==================== CONFIGURATION ====================
$CONFIG_FILE = Join-Path $HOME ".jupyter_git_config.ps1"
$DEFAULT_BRANCH = "main"
$WORKSPACE_PATH = Get-Location
# ========================================================

function Write-Color {
    param([string]$Message, [ConsoleColor]$Color)
    Write-Host $Message -ForegroundColor $Color
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

function Load-Config {
    if (Test-Path $CONFIG_FILE) {
        try {
            . $CONFIG_FILE
            # Map Python UI variables to global script variables
            $global:GLOBAL_GITHUB_REPO = $GITHUB_REPO
            $global:GLOBAL_CURRENT_BRANCH = if ([string]::IsNullOrWhiteSpace($CURRENT_BRANCH)) { $DEFAULT_BRANCH } else { $CURRENT_BRANCH }
            Write-Color "Config loaded: $global:GLOBAL_GITHUB_REPO" -Color Green
        } catch {
            Write-Color "Config corrupted. Please check your UI settings." -Color Yellow
            New-Config
        }
    } else {
        New-Config
    }
}

function New-Config {
    $repo = Read-Host "Enter GitHub repository URL"
    $branch = Read-Host "Enter branch name (default: main)"
    $global:GLOBAL_GITHUB_REPO = $repo
    $global:GLOBAL_CURRENT_BRANCH = if ([string]::IsNullOrWhiteSpace($branch)) { "main" } else { $branch }
    
    $configLines = @(
        "`$GITHUB_REPO = '$GLOBAL_GITHUB_REPO'",
        "`$CURRENT_BRANCH = '$GLOBAL_CURRENT_BRANCH'"
    )
    $configLines | Out-File -FilePath $CONFIG_FILE -Encoding utf8 -Force
}

function Execute-Git {
    param([string]$GitParams)
    # Capture Success (1) and Error (2) streams together
    $fullCommand = "git $GitParams 2>&1"
    $result = Invoke-Expression $fullCommand
    
    if ($LASTEXITCODE -ne 0) {
        Report-GitError -Command "git $GitParams" -RawOutput ($result -join "`n")
        return $null
    }
    return $result
}

function Main {
    # 0. Set Context
    Set-Location $WORKSPACE_PATH
    Write-Color "Starting Git Process in: $($WORKSPACE_PATH.Path)" -Color Cyan
    
    # 1. Fix Docker Ownership Issue (Safe Directory)
    # This prevents the script from crashing when Docker creates files as 'root'
    $safeDir = $WORKSPACE_PATH.Path.Replace('\', '/')
    git config --global --add safe.directory $safeDir 2>&1 | Out-Null

    # 2. Load Configuration (linked to your Python UI)
    Load-Config

    # 3. Handle Brand New Projects (Init)
    if (-not (Test-Path ".git")) {
        Write-Color "No .git found. Initializing new repository..." -Color Yellow
        $null = Execute-Git "init"
    }

    # 4. Handle Changes & Identity
    Write-Color "Checking for changes..." -Color Yellow
    $status = git status --porcelain 2>&1
    
    if (-not [string]::IsNullOrWhiteSpace($status)) {
        Write-Color "Changes found. Staging files..." -Color Green
        $null = Execute-Git "add ."
        
        # Identity check (prevent 'identity unknown' error)
        if ([string]::IsNullOrEmpty((git config user.name))) {
            git config user.email "jupyter@auto.push"
            git config user.name "Jupyter User"
        }
        
        Write-Host "Creating commit..."
        $null = Execute-Git "commit -m 'Auto-backup-$(Get-Date -Format 'HH-mm-ss')'"
    } else {
        Write-Color "No new changes to commit." -Color Gray
    }

    # 5. Remote Sync & Force Push
    if (-not [string]::IsNullOrEmpty($global:GLOBAL_GITHUB_REPO)) {
        Write-Color "Syncing with GitHub: $global:GLOBAL_GITHUB_REPO" -Color Magenta
        
        # Reset remote to ensure it matches the current UI config
        git remote remove origin 2>&1 | Out-Null
        $null = Execute-Git "remote add origin $global:GLOBAL_GITHUB_REPO"
        
        # The Force Push handles the 'rejected' error you saw earlier
        $pushResult = Execute-Git "push origin $global:GLOBAL_CURRENT_BRANCH --force"
        
        if ($null -ne $pushResult) {
            Write-Color "SUCCESS: Project backed up to $global:GLOBAL_CURRENT_BRANCH" -Color Green
        }
    }
}

# Run the process
Main