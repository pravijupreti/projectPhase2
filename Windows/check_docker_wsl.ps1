# save as check_docker_wsl.ps1
Write-Host "Checking WSL distributions..." -ForegroundColor Cyan
wsl -l -v

Write-Host "`nChecking for dockerd process..." -ForegroundColor Cyan
Get-Process -Name "dockerd" -ErrorAction SilentlyContinue

Write-Host "`nChecking Docker service..." -ForegroundColor Cyan
Get-Service -Name "com.docker.service" -ErrorAction SilentlyContinue

Write-Host "`nChecking Docker config folder..." -ForegroundColor Cyan
Test-Path "$env:APPDATA\Docker"