param(
  [string]$RepoRoot='C:\CK-NEXUS\workspace',
  [string]$InstallRoot='C:\CK-N8N'
)
$ErrorActionPreference='Stop'
$sidecar = Join-Path $RepoRoot 'integrations\n8n\ck_nexus_agent_sidecar.mjs'
$n8nStart = Join-Path $RepoRoot 'integrations\n8n\start_n8n_dev.ps1'
if (!(Test-Path $sidecar)) { throw "sidecar not found: $sidecar" }
if (!(Test-Path $n8nStart)) { throw "n8n launcher not found: $n8nStart" }
$env:CK_NEXUS_SIDECAR_HOST='127.0.0.1'
$env:CK_NEXUS_SIDECAR_PORT='8765'
$env:CK_NEXUS_AGENT_ENDPOINT='http://127.0.0.1:8765/v1/agent'
$node=(Get-Command node.exe -ErrorAction Stop).Source
$sidecarLog=Join-Path $InstallRoot 'sidecar.log'
$sidecarErr=Join-Path $InstallRoot 'sidecar.err.log'
Start-Process -FilePath $node -ArgumentList @($sidecar) -WindowStyle Hidden -RedirectStandardOutput $sidecarLog -RedirectStandardError $sidecarErr
Start-Sleep -Seconds 2
$health=Invoke-RestMethod -Uri 'http://127.0.0.1:8765/health' -TimeoutSec 5
if (-not $health.ok) { throw 'sidecar health check failed' }
Write-Host 'CK-NEXUS sidecar READY on 127.0.0.1:8765'
& $n8nStart -InstallRoot $InstallRoot
