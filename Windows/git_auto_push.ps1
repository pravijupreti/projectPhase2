# git_auto_push.ps1
param(
    [Parameter(Mandatory=$true)]
    [string]$WorkspacePath
)

$ErrorActionPreference = "Continue"
$CONFIG_FILE = Join-Path $HOME ".jupyter_git_config.ps1"

function Write-Color {
    param([string]$Message, [ConsoleColor]$Color)
    Write-Host $Message -ForegroundColor $Color
}

function Load-Config {
    if (Test-Path $CONFIG_FILE) {
        try {
            . $CONFIG_FILE
            $global:REPO_URL = $GITHUB_REPO
            $global:TARGET_BRANCH = $CURRENT_BRANCH
            Write-Color "Config loaded: $global:REPO_URL branch: $global:TARGET_BRANCH" -Color Green
        } catch {
            Write-Color "Config file corrupted: $_" -Color Red
            exit 1
        }
    } else {
        Write-Color "No config file found at $CONFIG_FILE - cannot push." -Color Red
        exit 1
    }
}

function Execute-Git {
    param([string]$GitParams)
    $result = Invoke-Expression "git $GitParams 2>&1"
    if ($LASTEXITCODE -ne 0) {
        Write-Color "GIT ERROR: git $GitParams" -Color Red
        Write-Host ($result -join "`n")
        return $null
    }
    return $result
}

if (-not (Test-Path $WorkspacePath)) {
    Write-Color "Workspace path not found: $WorkspacePath" -Color Red
    exit 1
}

Set-Location $WorkspacePath
Write-Color "Working directory: $WorkspacePath" -Color Cyan

$safePath = $WorkspacePath.Replace('\', '/')
git config --global --add safe.directory $safePath 2>&1 | Out-Null

Load-Config

if (-not (Test-Path ".git")) {
    Write-Color "No .git found - initialising new repository..." -Color Yellow
    Execute-Git "init" | Out-Null
    if (-not [string]::IsNullOrEmpty($global:REPO_URL)) {
        Execute-Git "remote add origin $global:REPO_URL" | Out-Null
    }
}

$currentRemote = git remote get-url origin 2>&1
if ($LASTEXITCODE -eq 0 -and $currentRemote.Trim() -ne $global:REPO_URL.Trim()) {
    Write-Color "Remote URL changed - updating origin..." -Color Yellow
    git remote set-url origin $global:REPO_URL 2>&1 | Out-Null
}

if ([string]::IsNullOrEmpty((git config user.name 2>&1))) {
    git config user.email "jupyter@auto.push"
    git config user.name "Jupyter Auto Push"
}

$status = git status --porcelain 2>&1
if (-not [string]::IsNullOrWhiteSpace($status)) {
    Write-Color "Changes detected - staging..." -Color Green
    Execute-Git "add ." | Out-Null
    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    Execute-Git "commit -m 'Auto-backup $timestamp'" | Out-Null
    Write-Color "Commit created." -Color Green
} else {
    Write-Color "No changes to commit." -Color Gray
}

if ([string]::IsNullOrEmpty($global:REPO_URL)) {
    Write-Color "No repo URL configured - skipping push." -Color Yellow
    exit 0
}

Write-Color "Pushing to $global:REPO_URL ($global:TARGET_BRANCH)..." -Color Magenta

git remote get-url origin 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Execute-Git "remote add origin $global:REPO_URL" | Out-Null
}

$pushResult = Execute-Git "push origin $global:TARGET_BRANCH"
if ($null -ne $pushResult) {
    Write-Color "PUSH SUCCESSFUL" -Color Green
} else {
    Write-Color "Retrying with --set-upstream..." -Color Yellow
    $pushResult = Execute-Git "push --set-upstream origin $global:TARGET_BRANCH"
    if ($null -ne $pushResult) {
        Write-Color "PUSH SUCCESSFUL (upstream set)" -Color Green
    } else {
        Write-Color "PUSH FAILED" -Color Red
        exit 1
    }
}
