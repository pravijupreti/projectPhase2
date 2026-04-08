# switch_branch.ps1
# Switches to specified branch and refreshes workspace
#
# Usage:
#   powershell -File switch_branch.ps1 -WorkspacePath "C:\workspace" -BranchName "main"

param(
    [Parameter(Mandatory=$true)]
    [string]$WorkspacePath,
    
    [Parameter(Mandatory=$true)]
    [string]$BranchName,
    
    [Parameter(Mandatory=$false)]
    [switch]$CreateNew
)

$ErrorActionPreference = "Continue"

function Write-Color {
    param([string]$Message, [ConsoleColor]$Color)
    Write-Host $Message -ForegroundColor $Color
}

# Validate workspace
if (-not (Test-Path $WorkspacePath)) {
    Write-Color "Workspace path not found: $WorkspacePath" -Color Red
    exit 1
}

Set-Location $WorkspacePath
Write-Color "Working directory: $WorkspacePath" -Color Cyan

# Check if it's a git repository
if (-not (Test-Path ".git")) {
    Write-Color "Not a git repository. Initializing..." -Color Yellow
    git init
}

# Fetch latest from remote (if remote exists)
$remoteUrl = git remote get-url origin 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Color "Fetching latest from remote..." -Color Cyan
    git fetch --all
}

# Switch branch
if ($CreateNew) {
    Write-Color "Creating and switching to new branch: $BranchName" -Color Yellow
    git checkout -b $BranchName
} else {
    Write-Color "Switching to branch: $BranchName" -Color Yellow
    
    # Check if branch exists locally
    $localBranch = git branch --list $BranchName
    if ($localBranch) {
        git checkout $BranchName
    } else {
        # Try to checkout from remote
        Write-Color "Branch not found locally, trying from remote..." -Color Yellow
        git checkout -b $BranchName origin/$BranchName 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Color "Branch not found. Creating new branch: $BranchName" -Color Yellow
            git checkout -b $BranchName
        }
    }
}

if ($LASTEXITCODE -eq 0) {
    Write-Color "Successfully switched to branch: $BranchName" -Color Green
    
    # Pull latest changes if switching to existing branch
    if (-not $CreateNew) {
        Write-Color "Pulling latest changes..." -Color Cyan
        git pull origin $BranchName
    }
    
    # Show current status
    Write-Color "`nCurrent branch status:" -Color Cyan
    git status --short
    
    Write-Color "`nBranch switch completed!" -Color Green
} else {
    Write-Color "Failed to switch to branch: $BranchName" -Color Red
    exit 1
}