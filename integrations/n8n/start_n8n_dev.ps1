param([string]$InstallRoot='C:\CK-N8N')
$ErrorActionPreference='Stop'
$n8n = Join-Path $InstallRoot 'node_modules\.bin\n8n.cmd'
if (!(Test-Path $n8n)) { throw 'n8n not installed; run install_n8n_windows.ps1 first' }
$env:N8N_USER_FOLDER = Join-Path $InstallRoot 'data'
$env:N8N_PORT = '5678'
$env:N8N_LISTEN_ADDRESS = '127.0.0.1'
$env:N8N_SECURE_COOKIE = 'false'
$env:N8N_DIAGNOSTICS_ENABLED = 'false'
$env:N8N_VERSION_NOTIFICATIONS_ENABLED = 'false'
$env:N8N_PERSONALIZATION_ENABLED = 'false'
$env:N8N_TEMPLATES_ENABLED = 'false'
$env:N8N_BLOCK_ENV_ACCESS_IN_NODE = 'false'
if (-not $env:CK_NEXUS_AGENT_ENDPOINT) { $env:CK_NEXUS_AGENT_ENDPOINT='http://127.0.0.1:8000/api/dev-agent' }
& $n8n start
