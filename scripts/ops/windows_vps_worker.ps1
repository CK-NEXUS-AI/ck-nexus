param(
    [string]$WorkerRoot = "C:\CKTools",
    [switch]$SkipRemoteAgent,
    [switch]$PersistRemoteAgent,
    [switch]$InstallPythonToolchain,
    [switch]$InstallGitToolchain
)

$ErrorActionPreference = "Stop"

function Assert-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Run this script from an elevated PowerShell session."
    }
}

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
    $nodeExe = Join-Path $nodeDir "node.exe"
    if (Test-Path $nodeExe) { return $nodeDir }

    New-Item -ItemType Directory -Force -Path $WorkerRoot | Out-Null
    if (Test-Path $nodeDir) { Remove-Item -Recurse -Force $nodeDir }

    $index = Invoke-RestMethod "https://nodejs.org/dist/index.json"
    $version = $index | Where-Object { $_.lts } | Select-Object -First 1 -ExpandProperty version
    if (-not $version) { throw "Unable to resolve Node.js LTS version." }

    $archiveName = "node-$version-win-x64.zip"
    $zip = Join-Path $env:TEMP ("node-$version-" + [guid]::NewGuid().ToString("N") + ".zip")
    Invoke-WebRequest -UseBasicParsing "https://nodejs.org/dist/$version/$archiveName" -OutFile $zip

    $sumText = (Invoke-WebRequest -UseBasicParsing "https://nodejs.org/dist/$version/SHASUMS256.txt").Content
    $match = [regex]::Match($sumText, "(?m)^([0-9a-fA-F]{64})\s+$([regex]::Escape($archiveName))$")
    if (-not $match.Success) { throw "Unable to resolve Node.js checksum." }
    $actual = (Get-FileHash -Algorithm SHA256 $zip).Hash.ToLowerInvariant()
    if ($actual -ne $match.Groups[1].Value.ToLowerInvariant()) { throw "Node.js checksum mismatch." }

    $expanded = Join-Path $WorkerRoot "node-$version-win-x64"
    if (Test-Path $expanded) { Remove-Item -Recurse -Force $expanded }
    Expand-Archive $zip -DestinationPath $WorkerRoot -Force
    Move-Item $expanded $nodeDir
    Remove-Item $zip -Force

    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    if ($machinePath -notlike "*$nodeDir*") {
        [Environment]::SetEnvironmentVariable("Path", "$machinePath;$nodeDir", "Machine")
    }
    return $nodeDir
}

function Ensure-Uv {
    $uvDir = Join-Path $WorkerRoot "uv"
    $uvExe = Join-Path $uvDir "uv.exe"
    if (Test-Path $uvExe) { return $uvExe }

    New-Item -ItemType Directory -Force -Path $uvDir | Out-Null
    $release = Invoke-RestMethod "https://api.github.com/repos/astral-sh/uv/releases/latest"
    $archiveName = "uv-x86_64-pc-windows-msvc.zip"
    $asset = $release.assets | Where-Object { $_.name -eq $archiveName } | Select-Object -First 1
    $checksumAsset = $release.assets | Where-Object { $_.name -eq "$archiveName.sha256" } | Select-Object -First 1
    if (-not $asset -or -not $checksumAsset) { throw "Unable to resolve uv release assets." }

    $zip = Join-Path $env:TEMP ("uv-" + [guid]::NewGuid().ToString("N") + ".zip")
    $sumFile = "$zip.sha256"
    Invoke-WebRequest -UseBasicParsing $asset.browser_download_url -OutFile $zip
    Invoke-WebRequest -UseBasicParsing $checksumAsset.browser_download_url -OutFile $sumFile
    $expected = ((Get-Content $sumFile -Raw).Trim() -split "\s+")[0].ToLowerInvariant()
    $actual = (Get-FileHash -Algorithm SHA256 $zip).Hash.ToLowerInvariant()
    if ($actual -ne $expected) { throw "uv checksum mismatch." }

    Expand-Archive $zip -DestinationPath $uvDir -Force
    Remove-Item $zip,$sumFile -Force
    if (-not (Test-Path $uvExe)) { throw "uv executable missing after extraction." }
    return $uvExe
}

function Ensure-MinGit {
    $gitDir = Join-Path $WorkerRoot "git"
    $gitExe = Join-Path $gitDir "cmd\git.exe"
    if (Test-Path $gitExe) { return $gitExe }

    $headers = @{ "User-Agent" = "CK-NEXUS-worker" }
    $release = Invoke-RestMethod -Headers $headers "https://api.github.com/repos/git-for-windows/git/releases/latest"
    $asset = $release.assets | Where-Object { $_.name -match '^MinGit-.*-64-bit\.zip$' } | Select-Object -First 1
    if (-not $asset) { throw "Unable to resolve MinGit x64 release asset." }
    if (-not $asset.digest -or $asset.digest -notmatch '^sha256:[0-9a-fA-F]{64}$') {
        throw "GitHub release asset is missing a SHA-256 digest."
    }

    $zip = Join-Path $env:TEMP ("mingit-" + [guid]::NewGuid().ToString("N") + ".zip")
    Invoke-WebRequest -UseBasicParsing $asset.browser_download_url -OutFile $zip
    $expected = ($asset.digest -replace '^sha256:','').ToLowerInvariant()
    $actual = (Get-FileHash -Algorithm SHA256 $zip).Hash.ToLowerInvariant()
    if ($actual -ne $expected) { throw "MinGit checksum mismatch." }

    if (Test-Path $gitDir) { Remove-Item -Recurse -Force $gitDir }
    New-Item -ItemType Directory -Force -Path $gitDir | Out-Null
    Expand-Archive $zip -DestinationPath $gitDir -Force
    Remove-Item -Force $zip
    if (-not (Test-Path $gitExe)) { throw "git executable missing after extraction." }
    return $gitExe
}

function Register-RemoteAgentTask([string]$nodeDir) {
    $deviceFile = Join-Path $env:USERPROFILE ".desktop-commander-device\device.json"
    if (-not (Test-Path $deviceFile)) {
        throw "Authorize Desktop Commander once before using -PersistRemoteAgent."
    }

    $launcher = Join-Path $WorkerRoot "start-desktop-commander.cmd"
    $log = Join-Path $WorkerRoot "desktop-commander.log"
    $npx = Join-Path $nodeDir "npx.cmd"
    $launcherBody = "@echo off`r`nset PATH=$nodeDir;%PATH%`r`n`"$npx`" -y @wonderwhy-er/desktop-commander@latest remote >> `"$log`" 2>&1`r`n"
    Set-Content -Path $launcher -Value $launcherBody -Encoding Ascii

    $taskName = "CK-NEXUS-DesktopCommander"
    $userId = "$env:USERDOMAIN\$env:USERNAME"
    $action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$launcher`""
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $userId
    $principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType Interactive -RunLevel Highest
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Force | Out-Null
    Start-ScheduledTask -TaskName $taskName
    Write-Output "REMOTE_AGENT_TASK=$taskName"
}

Assert-Administrator
Ensure-OpenSshServer
$nodeDir = Ensure-NodeLts
& (Join-Path $nodeDir "node.exe") --version
& (Join-Path $nodeDir "npm.cmd") --version

if ($InstallPythonToolchain) {
    $uvExe = Ensure-Uv
    & $uvExe --version
    & $uvExe python install 3.12
    & $uvExe python find 3.12
}

if ($InstallGitToolchain) {
    $gitExe = Ensure-MinGit
    & $gitExe --version
}

Write-Output "SSHD=$((Get-Service sshd).Status)"
Write-Output "WORKER_ROOT=$WorkerRoot"

if ($PersistRemoteAgent) {
    Register-RemoteAgentTask $nodeDir
} elseif (-not $SkipRemoteAgent) {
    Write-Output "Starting Desktop Commander device authorization flow..."
    & (Join-Path $nodeDir "npx.cmd") -y "@wonderwhy-er/desktop-commander@latest" remote
}
