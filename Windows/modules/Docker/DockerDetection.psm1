# modules/Docker/DockerDetection.psm1
# Docker detection functions

function Test-DockerDaemonResponding {
    docker version --format '{{.Server.Version}}' > $null 2>&1
    return ($LASTEXITCODE -eq 0)
}

function Test-DockerInstalled {
    return (Get-Command docker -ErrorAction SilentlyContinue) -ne $null
}

function Test-DockerDesktopInstalled {
    $paths = @(
        "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe",
        "$env:LOCALAPPDATA\Docker\Docker Desktop.exe"
    )
    foreach ($p in $paths) {
        if (Test-Path $p) { return $p }
    }
    return $null
}

Export-ModuleMember -Function Test-DockerDaemonResponding, Test-DockerInstalled, Test-DockerDesktopInstalled