param(
    [Parameter(Mandatory=$true)] [string]$TargetBranch,
    [Parameter(Mandatory=$false)] [switch]$CreateNew,
    [Parameter(Mandatory=$false)] [switch]$ListOnly,
    [Parameter(Mandatory=$false)] [string]$BaseCommit
)

$ErrorActionPreference = "Continue" 
if ($PSScriptRoot -like "*\Windows") { Set-Location "$PSScriptRoot\.." }

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

# --- Add this to the LISTING section of manage_branch.ps1 ---
if ($ListOnly) {
    # We use -vv to get the upstream tracking information
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

try {
    if ($CreateNew) {
        if ($BaseCommit) { git checkout -b $TargetBranch $BaseCommit }
        else { git checkout -b $TargetBranch }
    } else {
        git checkout $TargetBranch
    }
    Show-GitTree
} catch {
    Write-Data "ERROR" "Operation failed: $_"
    Show-GitTree
}