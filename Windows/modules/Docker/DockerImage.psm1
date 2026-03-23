# modules/Docker/DockerImage.psm1
# Docker image pull operations

function Pull-DockerImage {
    param([string]$image)

    Write-Host "`n⬇ Pulling Docker image: $image"
    Write-Host ("=" * 60)

    try {
        # Run docker pull and stream output live
        docker pull $image 2>&1 | ForEach-Object {
            Write-Host $_
        }

        if ($LASTEXITCODE -eq 0) {
            Write-Host "`n✅ Image download completed"
            return $true
        }
        else {
            Write-Host "`n❌ Image pull failed"
            return $false
        }
    }
    catch {
        Write-Host "`n❌ Docker pull error: $_"
        return $false
    }
}

Export-ModuleMember -Function Pull-DockerImage