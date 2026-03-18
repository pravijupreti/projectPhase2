# git_auto_push.ps1
$ErrorActionPreference = "Continue"

# --- CONFIGURATION ---
$CONFIG_FILE = Join-Path $HOME ".jupyter_git_config.ps1"
$DEFAULT_BRANCH = "main"
$WORKSPACE_PATH = Get-Location
# ---------------------

function Write-Color {
    param([string]$Message, [ConsoleColor]$Color)
    Write-Host $Message -ForegroundColor $Color
}

function Report-GitError {
    param([string]$Command, [string]$RawOutput)
    Write-Host "`n"
    Write-Color "GIT ERROR DETECTED" -Color Red
    Write-Color "Command: $Command" -Color Yellow
    Write-Color "Exit Code: $LASTEXITCODE" -Color White
    Write-Color "RAW SYSTEM MESSAGE:" -Color Cyan
    Write-Host $RawOutput
    Write-Host "`n"
}

function Load-Config {
    if (Test-Path $CONFIG_FILE) {
        try {
            . $CONFIG_FILE
            $global:GLOBAL_GITHUB_REPO = $GITHUB_REPO
            $global:GLOBAL_CURRENT_BRANCH = $CURRENT_BRANCH
            Write-Color "Config loaded: $GLOBAL_GITHUB_REPO" -Color Green
        } catch {
            Write-Color "Config corrupted. Re-entering details." -Color Yellow
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
    
    # We use Invoke-Expression here for better handling of multi-part strings
    $fullCommand = "git $GitParams 2>&1"
    $result = Invoke-Expression $fullCommand
    
    if ($LASTEXITCODE -ne 0) {
        Report-GitError -Command "git $GitParams" -RawOutput ($result -join "`n")
        return $null
    }
    return $result
}

function Main {
    Set-Location $WORKSPACE_PATH
    Write-Color "Starting Git Process in: $($WORKSPACE_PATH.Path)" -Color Cyan
    
    # 1. Trust directory
    $safeDir = $WORKSPACE_PATH.Path.Replace('\', '/')
    git config --global --add safe.directory $safeDir 2>&1 | Out-Null

    # 2. Load settings
    Load-Config

    # 3. Initialize
    if (-not (Test-Path ".git")) {
        Write-Host "No .git found. Initializing..."
        Execute-Git "init" | Out-Null
    }

    # 4. Changes
    Write-Color "Checking for changes..." -Color Yellow
    $status = git status --porcelain 2>&1
    
    if (-not [string]::IsNullOrWhiteSpace($status)) {
        Write-Color "Changes found. Staging files..." -Color Green
        Execute-Git "add ." | Out-Null
        
        if ([string]::IsNullOrEmpty((git config user.name))) {
            git config user.email "jupyter@auto.push"
            git config user.name "Jupyter User"
        }
        
        Write-Host "Creating commit..."
        Execute-Git "commit -m 'Auto-backup-$(Get-Date -Format 'HH-mm-ss')'" | Out-Null
    } else {
        Write-Color "No changes to backup." -Color Gray
    }

    # 5. Push & Publish Logic
    if (-not [string]::IsNullOrEmpty($GLOBAL_GITHUB_REPO)) {
        Write-Color "Pushing to GitHub..." -Color Magenta
        
        # Reset remote to ensure it always matches current UI config
        git remote remove origin 2>&1 | Out-Null
        Execute-Git "remote add origin $GLOBAL_GITHUB_REPO" | Out-Null
        
        # FEATURE ADDITION: 
        # Using -u (upstream) ensures that even new branches are 'published' 
        # to the remote. --force ensures the backup always overwrites the remote.
        Write-Color "Publishing/Updating branch: $GLOBAL_CURRENT_BRANCH" -Color Yellow
        $pushResult = Execute-Git "push -u origin $GLOBAL_CURRENT_BRANCH --force"
        
        if ($null -ne $pushResult) {
            Write-Color "PUSH SUCCESSFUL" -Color Green
        }
    }
}

Main