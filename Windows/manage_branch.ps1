param(
    [Parameter(Mandatory=$true)] [string]$TargetBranch,
    [Parameter(Mandatory=$false)] [switch]$CreateNew,
    [Parameter(Mandatory=$false)] [switch]$ListOnly,
    [Parameter(Mandatory=$false)] [string]$BaseCommit,
    [Parameter(Mandatory=$false)] [string]$WorkspacePath
)

$ErrorActionPreference = "Continue"

# Use WorkspacePath if provided, otherwise fall back to script location
if ($WorkspacePath -and (Test-Path $WorkspacePath)) {
    Set-Location $WorkspacePath
    Write-Output "[LOG] Changed to workspace: $WorkspacePath"
} elseif ($PSScriptRoot -like "*\Windows") { 
    Set-Location "$PSScriptRoot\.."
    Write-Output "[LOG] Changed to parent of Windows folder: $(Get-Location)"
} else {
    Write-Output "[LOG] Staying in current directory: $(Get-Location)"
}

function Write-Data { param([string]$Type, [string]$Msg) Write-Output "[$Type]$Msg" }

function Show-GitTree {
    Write-Data "TREE" "CLEAR_TREE"
    $fmt = "%H::%d::%an::%ar::%s"
    $gitCmd = "git log --graph --all --date=relative --color=never -n 30 --decorate --format=format:'$fmt'"
    
    Invoke-Expression $gitCmd | ForEach-Object {
        $line = $_
        # If line contains a 40-character SHA
        if ($line -match "(?<sha>[a-f0-9]{40})::") {
            if ($line -match "^(?<graph>.*?)(?<sha>[a-f0-9]{40})::(?<data>.*)$") {
                Write-Data "TREE" "$($Matches['graph'])::$($Matches['sha'])::$($Matches['data'])"
            }
        } else {
            # Graph-only lines (connectors)
            Write-Data "TREE" "$line:: :: :: :: :: "
        }
    }
}

# --- Listing mode ---
if ($ListOnly) {
    # First, verify we're in a git repository
    $gitCheck = git rev-parse --git-dir 2>$null
    if (-not $gitCheck) {
        Write-Data "ERROR" "Not a git repository: $(Get-Location)"
        exit 1
    }
    
    # Get branches with tracking info
    git branch -vv | ForEach-Object {
        $line = $_.Trim()
        # Matches: * branch_name  sha [origin/remote_name] commit_msg
        if ($line -match "^\*?\s*(?<local>[^\s]+)\s+[a-f0-9]+\s+(\[(?<remote>[^\]]+)\])?") {
            $local = $Matches['local']
            $remote = if ($Matches['remote']) { $Matches['remote'] } else { "NO_UPSTREAM" }
            
            # Send as a special LINK type for the bottom UI
            Write-Data "LINK" "$local::$remote"
            
            # Keep sending standard BRANCH for the dropdown too
            Write-Data "BRANCH" $local
        }
    }
    Show-GitTree
    exit 0
}

# --- Branch operation mode ---
try {
    if ($CreateNew) {
        if ($BaseCommit) { 
            Write-Output "[LOG] Creating branch '$TargetBranch' from commit $BaseCommit"
            git checkout -b $TargetBranch $BaseCommit
        } else { 
            Write-Output "[LOG] Creating new branch '$TargetBranch' from current HEAD"
            git checkout -b $TargetBranch 
        }
    } else {
        Write-Output "[LOG] Switching to branch '$TargetBranch'"
        git checkout $TargetBranch
    }
    Show-GitTree
} catch {
    Write-Data "ERROR" "Operation failed: $_"
    Show-GitTree
}