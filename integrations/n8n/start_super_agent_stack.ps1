param(
  [string]$RepoRoot='C:\CK-NEXUS\workspace',
  [string]$InstallRoot='C:\CK-N8N'
)
$ErrorActionPreference='Stop'
$sidecar = Join-Path $RepoRoot 'integrations\n8n\ck_nexus_agent_sidecar.mjs'
$toolGateway = Join-Path $RepoRoot 'integrations\n8n\ck_nexus_dev_tool_gateway.mjs'
$n8nStart = Join-Path $RepoRoot 'integrations\n8n\start_n8n_dev.ps1'
foreach ($file in @($sidecar,$toolGateway,$n8nStart)) {
  if (!(Test-Path $file)) { throw "required runtime file not found: $file" }
}
$env:CK_NEXUS_SIDECAR_HOST='127.0.0.1'
$env:CK_NEXUS_SIDECAR_PORT='8765'
$env:CK_NEXUS_TOOL_HOST='127.0.0.1'
$env:CK_NEXUS_TOOL_PORT='8766'
$env:CK_NEXUS_TOOL_ENDPOINT='http://127.0.0.1:8766/v1/tool'
$env:CK_NEXUS_AGENT_ENDPOINT='http://127.0.0.1:8765/v1/agent'
$env:CK_NEXUS_REPO_ROOT=$RepoRoot
if (-not $env:CK_NEXUS_TOOL_TOKEN) {
  $env:CK_NEXUS_TOOL_TOKEN=[guid]::NewGuid().ToString('N')
}
$node=(Get-Command node.exe -ErrorAction Stop).Source
$toolLog=Join-Path $InstallRoot 'tool-gateway.log'
$toolErr=Join-Path $InstallRoot 'tool-gateway.err.log'
$sidecarLog=Join-Path $InstallRoot 'sidecar.log'
$sidecarErr=Join-Path $InstallRoot 'sidecar.err.log'
Start-Process -FilePath $node -ArgumentList @($toolGateway) -WindowStyle Hidden -RedirectStandardOutput $toolLog -RedirectStandardError $toolErr
Start-Process -FilePath $node -ArgumentList @($sidecar) -WindowStyle Hidden -RedirectStandardOutput $sidecarLog -RedirectStandardError $sidecarErr
Start-Sleep -Seconds 2
$toolHealth=Invoke-RestMethod -Uri 'http://127.0.0.1:8766/health' -TimeoutSec 5
if (-not $toolHealth.ok) { throw 'tool gateway health check failed' }
$sidecarHealth=Invoke-RestMethod -Uri 'http://127.0.0.1:8765/health' -TimeoutSec 5
if (-not $sidecarHealth.ok) { throw 'sidecar health check failed' }
if (-not $sidecarHealth.tool_token_configured) { throw 'sidecar tool token not configured' }
Write-Host 'CK-NEXUS tool gateway READY on 127.0.0.1:8766'
Write-Host 'CK-NEXUS sidecar READY on 127.0.0.1:8765'
Write-Host 'Ephemeral tool token configured for this process tree.'
& $n8nStart -InstallRoot $InstallRoot
