# modules/Jupyter/JupyterWait.psm1
# Wait for Jupyter server

function Wait-ForJupyter {
    param([int]$Port)

    $tries = 60
    Write-Host "Waiting for Jupyter..." -NoNewline

    for ($i = 1; $i -le $tries; $i++) {
        try {
            $r = Invoke-WebRequest "http://localhost:$Port" -UseBasicParsing -TimeoutSec 2
            if ($r.StatusCode -eq 200 -or $r.StatusCode -eq 302) {
                Write-Host ""
                Write-Host "Jupyter Ready"
                return $true
            }
        } catch {}

        Write-Host "." -NoNewline
        Start-Sleep 1
    }

    Write-Host ""
    Write-Host "Jupyter not responding"
    return $false
}

Export-ModuleMember -Function Wait-ForJupyter