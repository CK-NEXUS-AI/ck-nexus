param(
  [string]$InstallRoot = 'C:\CK-N8N',
  [string]$NodeRoot = 'C:\CKTools\node',
  [string]$N8nVersion = '2.35.7'
)
$ErrorActionPreference = 'Stop'
$npm = Join-Path $NodeRoot 'npm.cmd'
$node = Join-Path $NodeRoot 'node.exe'
if (!(Test-Path $npm) -or !(Test-Path $node)) { throw 'Pinned Node.js toolchain not found' }
New-Item -ItemType Directory -Force $InstallRoot | Out-Null
Set-Location $InstallRoot
if (!(Test-Path 'package.json')) { & $npm init -y | Out-Null }
$env:NODE_OPTIONS='--max-old-space-size=4096'
& $npm install "n8n@$N8nVersion" --save-exact --legacy-peer-deps
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
$env:CK_NEXUS_AGENT_ENDPOINT = 'http://127.0.0.1:8000/api/dev-agent'
$workflow = Resolve-Path (Join-Path $PSScriptRoot 'ck-nexus-development-agent-fabric.workflow.json')
& (Join-Path $InstallRoot 'node_modules\.bin\n8n.cmd') import:workflow --input=$workflow
Write-Host "n8n $N8nVersion installed in $InstallRoot"
Write-Host 'Start with: .\start_n8n_dev.ps1'
