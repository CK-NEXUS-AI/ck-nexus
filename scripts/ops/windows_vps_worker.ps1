param(
    [string]$WorkerRoot = "C:\CKTools",
    [switch]$SkipRemoteAgent
)

$ErrorActionPreference = "Stop"

function Ensure-OpenSshServer {
    $cap = Get-WindowsCapability -Online | Where-Object Name -like "OpenSSH.Server*"
    if ($cap.State -ne "Installed") {
        Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0 | Out-Null
    }
    Set-Service sshd -StartupType Automatic
    Start-Service sshd
    if (-not (Get-NetFirewallRule -Name "CK-NEXUS-SSH" -ErrorAction SilentlyContinue)) {
        New-NetFirewallRule -Name "CK-NEXUS-SSH" -DisplayName "CK-NEXUS SSH TCP 22" -Direction Inbound -Protocol TCP -LocalPort 22 -Action Allow | Out-Null
    }
}

function Ensure-NodeLts {
    $nodeDir = Join-Path $WorkerRoot "node"
    if (Test-Path (Join-Path $nodeDir "node.exe")) { return $nodeDir }
    New-Item -ItemType Directory -Force -Path $WorkerRoot | Out-Null
    $index = Invoke-RestMethod "https://nodejs.org/dist/index.json"
    $version = $index | Where-Object { $_.lts } | Select-Object -First 1 -ExpandProperty version
    $zip = Join-Path $env:TEMP ("node-$version-" + [guid]::NewGuid().ToString("N") + ".zip")
    Invoke-WebRequest "https://nodejs.org/dist/$version/node-$version-win-x64.zip" -OutFile $zip
    Expand-Archive $zip -DestinationPath $WorkerRoot -Force
    Rename-Item (Join-Path $WorkerRoot "node-$version-win-x64") "node"
    Remove-Item $zip -Force
    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    if ($machinePath -notlike "*$nodeDir*") {
        [Environment]::SetEnvironmentVariable("Path", "$machinePath;$nodeDir", "Machine")
    }
    return $nodeDir
}

Ensure-OpenSshServer
$nodeDir = Ensure-NodeLts
& (Join-Path $nodeDir "node.exe") --version
& (Join-Path $nodeDir "npm.cmd") --version

Write-Output "SSHD=$((Get-Service sshd).Status)"
Write-Output "WORKER_ROOT=$WorkerRoot"

if (-not $SkipRemoteAgent) {
    Write-Output "Starting Desktop Commander device authorization flow..."
    & (Join-Path $nodeDir "npx.cmd") -y "@wonderwhy-er/desktop-commander@latest" remote
}
