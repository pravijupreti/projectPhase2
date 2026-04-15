param(
    [Parameter(Mandatory=$true)] [string]$TargetBranch,
    [Parameter(Mandatory=$false)] [switch]$CreateNew,
    [Parameter(Mandatory=$false)] [switch]$ListOnly,
    [Parameter(Mandatory=$false)] [string]$BaseCommit,
    [Parameter(Mandatory=$false)] [string]$WorkspacePath
)

$ErrorActionPreference = "Continue"

# --- Workspace handling ---
if ($WorkspacePath -and (Test-Path $WorkspacePath)) {
    Set-Location $WorkspacePath
    Write-Output "[LOG] Changed to workspace: $WorkspacePath"
} elseif ($PSScriptRoot -like "*\Windows") { 
    Set-Location "$PSScriptRoot\.."
    Write-Output "[LOG] Changed to parent of Windows folder: $(Get-Location)"
} else {
    Write-Output "[LOG] Staying in current directory: $(Get-Location)"
}

function Write-Data { 
    param([string]$Type, [string]$Msg) 
    Write-Output "[$Type]$Msg" 
}

# --- Debug Info ---
function Show-DebugInfo {
    Write-Output "===== DEBUG: CURRENT PATH ====="
    Write-Output (Get-Location)

    Write-Output "===== DEBUG: REPO ROOT ====="
    git rev-parse --show-toplevel 2>$null

    Write-Output "===== DEBUG: REMOTES ====="
    git remote -v

    Write-Output "===== DEBUG: STATUS ====="
    git status

    Write-Output "===== DEBUG: git branch ====="
    git branch

    Write-Output "===== DEBUG: git branch -a ====="
    git branch -a

    Write-Output "===== DEBUG: git branch -r ====="
    git branch -r

    Write-Output "===== DEBUG: git for-each-ref ====="
    git for-each-ref --format="%(refname:short)"
}

# --- Git Tree ---
function Show-GitTree {
    Write-Data "TREE" "CLEAR_TREE"
    $fmt = "%H::%d::%an::%ar::%s"
    $gitCmd = "git log --graph --all --date=relative --color=never -n 30 --decorate --format=format:'$fmt'"
    
    Invoke-Expression $gitCmd | ForEach-Object {
        $line = $_
        if ($line -match "(?<sha>[a-f0-9]{40})::") {
            if ($line -match "^(?<graph>.*?)(?<sha>[a-f0-9]{40})::(?<data>.*)$") {
                Write-Data "TREE" "$($Matches['graph'])::$($Matches['sha'])::$($Matches['data'])"
            }
        } else {
            Write-Data "TREE" "$line:: :: :: :: :: "
        }
    }
}

# --- Listing mode ---
if ($ListOnly) {

    $gitCheck = git rev-parse --git-dir 2>$null
    if (-not $gitCheck) {
        Write-Data "ERROR" "Not a git repository: $(Get-Location)"
        exit 1
    }

    # Always sync with remote
    git fetch --all | Out-Null

    $seen = @{}

    Write-Output "===== DEBUG: LOCAL BRANCHES ====="
    $localBranches = git for-each-ref --format="%(refname:short)" refs/heads
    $localBranches | ForEach-Object { Write-Output "LOCAL: $_" }

    foreach ($branch in $localBranches) {
        $branch = $branch.Trim()
        if (-not $branch) { continue }

        $seen[$branch] = $true

        # upstream (safe)
        $upstream = git for-each-ref --format="%(upstream:short)" "refs/heads/$branch"

        if ($upstream) {
            Write-Data "LINK" "$branch::$upstream"
        } else {
            Write-Data "LINK" "$branch::LOCAL"
        }

        Write-Data "BRANCH" $branch
    }

    Write-Output "===== DEBUG: REMOTE BRANCHES ====="
    $remoteBranches = git for-each-ref --format="%(refname:short)" refs/remotes
    $remoteBranches | ForEach-Object { Write-Output "REMOTE: $_" }

    foreach ($branch in $remoteBranches) {
        $branch = $branch.Trim()
        if ($branch -notmatch "^origin/") { continue }
        
        if (-not $branch) { continue }
        if ($branch -match "HEAD") { continue }

        # Remove origin/ prefix
        if ($branch -match "^origin/(.+)") {
            $cleanName = $Matches[1]
        } else {
            $cleanName = $branch
        }

        # Skip if already exists locally
        if ($seen.ContainsKey($cleanName)) { continue }

        Write-Data "LINK" "$cleanName::REMOTE"
        Write-Data "BRANCH" $cleanName
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