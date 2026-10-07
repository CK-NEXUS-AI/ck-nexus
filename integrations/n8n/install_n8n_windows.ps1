param(
  [string]$InstallRoot = 'C:\CK-N8N',
  [string]$NodeRoot = 'C:\CKTools\node',
  [string]$N8nVersion = '2.35.7',
  [int]$MinimumFreeMemoryMB = 1400
)
$ErrorActionPreference = 'Stop'
$npm = Join-Path $NodeRoot 'npm.cmd'
$node = Join-Path $NodeRoot 'node.exe'
if (!(Test-Path $npm) -or !(Test-Path $node)) { throw 'Pinned Node.js toolchain not found' }
New-Item -ItemType Directory -Force $InstallRoot | Out-Null
$lockPath = Join-Path $InstallRoot '.install.lock'
if (Test-Path $lockPath) {
  $oldPid = (Get-Content $lockPath -ErrorAction SilentlyContinue | Select-Object -First 1)
  if ($oldPid -and (Get-Process -Id ([int]$oldPid) -ErrorAction SilentlyContinue)) {
    throw "another n8n install owns the lock (PID $oldPid)"
  }
  Remove-Item $lockPath -Force -ErrorAction SilentlyContinue
}
Set-Content -Path $lockPath -Value $PID -Encoding ascii
try {
  $otherInstalls = Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
    $_.ProcessId -ne $PID -and $_.CommandLine -match 'npm(-cli)?\.js.*\binstall\b'
  }
  if ($otherInstalls) { throw 'another npm install is running on this worker; retry after it finishes' }
  $os = Get-CimInstance Win32_OperatingSystem -ErrorAction Stop
  $freeMB = [math]::Floor([double]$os.FreePhysicalMemory / 1024)
  if ($freeMB -lt $MinimumFreeMemoryMB) {
    throw "insufficient free memory for n8n install: ${freeMB}MB < ${MinimumFreeMemoryMB}MB"
  }
  Set-Location $InstallRoot
  if (!(Test-Path 'package.json')) { & $npm init -y | Out-Null }
  $env:NODE_OPTIONS='--max-old-space-size=4096'
  & $npm install "n8n@$N8nVersion" --save-exact --legacy-peer-deps --no-audit --no-fund
  if ($LASTEXITCODE -ne 0) { throw 'n8n install failed' }
  $env:N8N_USER_FOLDER = Join-Path $InstallRoot 'data'
  $env:N8N_PORT = '5678'
  $env:N8N_LISTEN_ADDRESS = '127.0.0.1'
  $env:N8N_SECURE_COOKIE = 'false'
  $env:N8N_DIAGNOSTICS_ENABLED = 'false'
  $env:N8N_VERSION_NOTIFICATIONS_ENABLED = 'false'
  $env:N8N_PERSONALIZATION_ENABLED = 'false'
  $env:N8N_TEMPLATES_ENABLED = 'false'
  $env:N8N_BLOCK_ENV_ACCESS_IN_NODE = 'false'
  $env:CK_NEXUS_AGENT_ENDPOINT = 'http://127.0.0.1:8765/v1/agent'
  $n8n = Join-Path $InstallRoot 'node_modules\.bin\n8n.cmd'
  $legacy = Resolve-Path (Join-Path $PSScriptRoot 'ck-nexus-development-agent-fabric.workflow.json')
  $super = Resolve-Path (Join-Path $PSScriptRoot 'ck-nexus-super-agent-fabric.v2.workflow.json')
  & $n8n import:workflow --input=$legacy
  if ($LASTEXITCODE -ne 0) { throw 'legacy workflow import failed' }
  & $n8n import:workflow --input=$super
  if ($LASTEXITCODE -ne 0) { throw 'super-agent v2 workflow import failed' }
  Write-Host "n8n $N8nVersion installed in $InstallRoot"
  Write-Host 'Imported legacy and Super-Agent v2 workflows (inactive by default).'
  Write-Host 'Next: start_super_agent_stack.ps1, run smoke_super_agent.ps1, then run n8n audit.'
} finally {
  Remove-Item $lockPath -Force -ErrorAction SilentlyContinue
}
