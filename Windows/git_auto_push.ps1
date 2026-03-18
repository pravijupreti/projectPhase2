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
    $fullCommand = "git $GitParams 2>&1"
    $result = Invoke-Expression $fullCommand
    if ($LASTEXITCODE -ne 0) {
        Write-Color "GIT ERROR: $result" -Color Red
        return $null
    }
    return $result
}

function Main {
    Set-Location $WORKSPACE_PATH
    
    # 1. Load config saved by Python UI
    if (Test-Path $CONFIG_FILE) { . $CONFIG_FILE }
    if (-not $GITHUB_REPO) { Write-Color "No Repo URL found!" -Color Red; return }

    # 2. Add and Commit
    Write-Color "Staging changes..." -Color Yellow
    Execute-Git "add ." | Out-Null
    
    # Ensure a dummy identity exists so commit doesn't fail
    git config user.email "jupyter@auto.push"
    git config user.name "Jupyter User"
    
    $date = Get-Date -Format "yyyy-MM-dd HH:mm"
    Execute-Git "commit -m 'Auto-backup: $date'" | Out-Null

    # 3. The "VS Code Style" Push
    Write-Color "Pushing $CURRENT_BRANCH to GitHub..." -Color Magenta
    
    # Refresh the remote
    git remote remove origin 2>&1 | Out-Null
    
    # TIP: If using a Token, the URL should be: 
    # https://<token>@github.com/username/repo.git
    Execute-Git "remote add origin $GITHUB_REPO" | Out-Null

    # Push with upstream tracking and force
    $push = Execute-Git "push -u origin $CURRENT_BRANCH --force"

    if ($null -ne $push) {
        Write-Color "✅ PUSH VERIFIED: Check GitHub for branch '$CURRENT_BRANCH'" -Color Green
    } else {
        Write-Color "❌ PUSH FAILED: Git couldn't reach the server." -Color Red
    }
}

Main