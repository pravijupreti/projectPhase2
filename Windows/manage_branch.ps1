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

if ($ListOnly) {
    # List local and remote branches
    git branch -a | ForEach-Object {
        $name = $_.Replace("*", "").Replace("remotes/origin/", "").Trim()
        if ($name -and $name -notmatch "HEAD ->") { Write-Data "BRANCH" $name }
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