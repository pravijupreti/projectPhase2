# modules/Jupyter/JupyterBrowser.psm1
# Browser operations

function Open-Browser {
    param([string]$Url)

    Write-Host "Opening browser $Url"

    $process = Start-Process $Url -PassThru
    $process.Id | Out-File "$env:TEMP\jupyter_browser.pid"
}

function Monitor-Browser {
    param([string]$Container)

    $pidfile = "$env:TEMP\jupyter_browser.pid"

    if (!(Test-Path $pidfile)) { return }

    $browserPid = [int](Get-Content $pidfile)

    Write-Host "Monitoring browser window..."

    while ($true) {
        Start-Sleep 2
        try {
            Get-Process -Id $browserPid -ErrorAction Stop > $null
        } catch {
            break
        }
    }

    Write-Host "Browser closed → triggering git push"

    $gitScript = Join-Path $PSScriptRoot "git_auto_push.ps1"

    if (Test-Path $gitScript) {
        Write-Host "Running git_auto_push.ps1..."

        try {
            powershell -ExecutionPolicy Bypass -File "$gitScript" "window_closed" 2>&1 | ForEach-Object {
                Write-Host $_
            }
            Write-Host "Git script finished"
        } catch {
            Write-Host "Git script ERROR:" -ForegroundColor Red
            Write-Host $_
        }
    } else {
        Write-Host "git_auto_push.ps1 not found!" -ForegroundColor Red
    }

    Remove-Item $pidfile -Force -ErrorAction SilentlyContinue
}

Export-ModuleMember -Function Open-Browser, Monitor-Browser