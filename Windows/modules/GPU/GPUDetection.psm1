# modules/GPU/GPUDetection.psm1
# GPU detection functions

function Test-NvidiaGPU {
    try {
        $gpu = Get-WmiObject Win32_VideoController | Where-Object { $_.Name -like "*NVIDIA*" }
        if ($gpu) { return $true }

        $nvidia = Get-Command nvidia-smi -ErrorAction SilentlyContinue
        if ($nvidia) {
            $out = & nvidia-smi --query-gpu=name --format=csv,noheader 2>$null
            if ($out) { return $true }
        }
    } catch {}
    return $false
}

Export-ModuleMember -Function Test-NvidiaGPU