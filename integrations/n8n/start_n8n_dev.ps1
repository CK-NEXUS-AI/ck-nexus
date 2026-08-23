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
$env:N8N_COMMUNITY_PACKAGES_ENABLED = 'false'
$env:N8N_UNVERIFIED_PACKAGES_ENABLED = 'false'
$env:N8N_PUBLIC_API_DISABLED = 'true'
$env:N8N_RUNNERS_TASK_TIMEOUT = '60'
$env:N8N_COMPRESSION_NODE_MAX_DECOMPRESSED_SIZE_BYTES = '268435456'
$env:N8N_COMPRESSION_NODE_MAX_ZIP_ENTRIES = '1000'
$env:N8N_BLOCK_ENV_ACCESS_IN_NODE = 'false'
if (-not $env:CK_NEXUS_AGENT_ENDPOINT) {
  $env:CK_NEXUS_AGENT_ENDPOINT='http://127.0.0.1:8765/v1/agent'
}
Write-Host "CK-NEXUS n8n development instance: http://127.0.0.1:5678"
Write-Host "Agent endpoint: $env:CK_NEXUS_AGENT_ENDPOINT"
& $n8n start
