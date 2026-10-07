param(
  [string]$RepoRoot='C:\CK-NEXUS\workspace',
  [string]$InstallRoot='C:\CK-N8N'
)
$ErrorActionPreference='Stop'
$sidecar = Join-Path $RepoRoot 'integrations\n8n\ck_nexus_agent_sidecar.mjs'
$toolGateway = Join-Path $RepoRoot 'integrations\n8n\ck_nexus_dev_tool_gateway.mjs'
$openaiAdapter = Join-Path $RepoRoot 'integrations\n8n\ck_nexus_openai_dev_adapter.mjs'
$n8nStart = Join-Path $RepoRoot 'integrations\n8n\start_n8n_dev.ps1'
foreach ($file in @($sidecar,$toolGateway,$openaiAdapter,$n8nStart)) {
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
if (-not $env:CK_NEXUS_INTELLIGENCE_TOKEN) {
  $env:CK_NEXUS_INTELLIGENCE_TOKEN=[guid]::NewGuid().ToString('N')
}
$useOpenAI = [bool]$env:OPENAI_API_KEY -and [bool]$env:CK_NEXUS_OPENAI_MODEL
if ($useOpenAI) {
  $env:CK_NEXUS_INTELLIGENCE_HOST='127.0.0.1'
  $env:CK_NEXUS_INTELLIGENCE_PORT='8767'
  $env:CK_NEXUS_INTELLIGENCE_ENDPOINT='http://127.0.0.1:8767/v1/intelligence'
} else {
  Remove-Item Env:CK_NEXUS_INTELLIGENCE_ENDPOINT -ErrorAction SilentlyContinue
}
$node=(Get-Command node.exe -ErrorAction Stop).Source
$toolLog=Join-Path $InstallRoot 'tool-gateway.log'
$toolErr=Join-Path $InstallRoot 'tool-gateway.err.log'
$sidecarLog=Join-Path $InstallRoot 'sidecar.log'
$sidecarErr=Join-Path $InstallRoot 'sidecar.err.log'
$intelligenceLog=Join-Path $InstallRoot 'intelligence.log'
$intelligenceErr=Join-Path $InstallRoot 'intelligence.err.log'
Start-Process -FilePath $node -ArgumentList @($toolGateway) -WindowStyle Hidden -RedirectStandardOutput $toolLog -RedirectStandardError $toolErr
if ($useOpenAI) {
  Start-Process -FilePath $node -ArgumentList @($openaiAdapter) -WindowStyle Hidden -RedirectStandardOutput $intelligenceLog -RedirectStandardError $intelligenceErr
}
Start-Process -FilePath $node -ArgumentList @($sidecar) -WindowStyle Hidden -RedirectStandardOutput $sidecarLog -RedirectStandardError $sidecarErr
Start-Sleep -Seconds 2
$toolHealth=Invoke-RestMethod -Uri 'http://127.0.0.1:8766/health' -TimeoutSec 5
if (-not $toolHealth.ok) { throw 'tool gateway health check failed' }
if ($useOpenAI) {
  $intelligenceHealth=Invoke-RestMethod -Uri 'http://127.0.0.1:8767/health' -TimeoutSec 5
  if (-not $intelligenceHealth.ok) { throw 'OpenAI development adapter health check failed' }
  if (-not $intelligenceHealth.api_key_configured -or -not $intelligenceHealth.model_configured) { throw 'OpenAI development adapter configuration incomplete' }
}
$sidecarHealth=Invoke-RestMethod -Uri 'http://127.0.0.1:8765/health' -TimeoutSec 5
if (-not $sidecarHealth.ok) { throw 'sidecar health check failed' }
if (-not $sidecarHealth.tool_token_configured) { throw 'sidecar tool token not configured' }
Write-Host 'CK-NEXUS tool gateway READY on 127.0.0.1:8766'
Write-Host 'CK-NEXUS sidecar READY on 127.0.0.1:8765'
if ($useOpenAI) {
  Write-Host "CK-NEXUS OpenAI development adapter READY on 127.0.0.1:8767 (model configured: $env:CK_NEXUS_OPENAI_MODEL)"
} else {
  Write-Host 'No OpenAI development credential/model configured; Sidecar remains PROPOSAL_ONLY.'
}
Write-Host 'Ephemeral tool/intelligence tokens configured for this process tree.'
& $n8nStart -InstallRoot $InstallRoot
