param([string]$WorkerRoot = "C:\CKTools")

$ErrorActionPreference = "Stop"
$fail = $false

function Check([string]$Name, [scriptblock]$Probe) {
    try {
        $ok = & $Probe
        if ($ok) { Write-Output "PASS  $Name" }
        else { Write-Output "FAIL  $Name"; $script:fail = $true }
    } catch {
        Write-Output "FAIL  $Name :: $($_.Exception.Message)"
        $script:fail = $true
    }
}

$node = Join-Path $WorkerRoot "node\node.exe"
$npm = Join-Path $WorkerRoot "node\npm.cmd"
$uv = Join-Path $WorkerRoot "uv\uv.exe"
$git = Join-Path $WorkerRoot "git\cmd\git.exe"
$device = Join-Path $env:USERPROFILE ".desktop-commander-device\device.json"
$taskName = "CK-NEXUS-DesktopCommander"

Write-Output "CK-NEXUS Windows VPS Worker Verification"
Write-Output "host=$(hostname)"
Check "Windows platform" {
    [System.Runtime.InteropServices.RuntimeInformation]::IsOSPlatform(
        [System.Runtime.InteropServices.OSPlatform]::Windows
    )
}
Check "OpenSSH running" { (Get-Service sshd).Status -eq "Running" }
Check "Node.js present" { Test-Path $node }
Check "npm present" { Test-Path $npm }
Check "uv present" { Test-Path $uv }
Check "Python 3.12 resolvable" { (Test-Path $uv) -and ((& $uv python find 3.12) -ne $null) }
Check "Git present" { Test-Path $git }
Check "Desktop Commander enrollment" { Test-Path $device }
Check "persistent task registered" { $null -ne (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) }

if ($fail) {
    Write-Output "WINDOWS_WORKER_READINESS=FAIL"
    exit 1
}
Write-Output "WINDOWS_WORKER_READINESS=PASS_CANDIDATE"
Write-Output "NOTE=Development worker readiness only; not Q12 or Production evidence."
