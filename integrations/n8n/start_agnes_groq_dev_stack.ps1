param(
  [string]$RepoRoot='C:\CK-NEXUS\n8n-agent-worktree',
  [string]$InstallRoot='C:\CK-N8N',
  [string]$GroqKeyFile='C:\CK-N8N\secure\groq-api-key.dpapi',
  [string]$GroqModel='openai/gpt-oss-120b',
  [int]$ToolPort=8766,
  [int]$IntelligencePort=8767,
  [int]$SidecarPort=8776
)

$ErrorActionPreference='Stop'

function Assert-PortFree([int]$Port) {
  $listener=Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
  if($listener){ throw "development port already in use: $Port" }
}

function Wait-Health([string]$Uri,[string]$Name) {
  for($i=0;$i -lt 20;$i++){
    try {
      $health=Invoke-RestMethod -Uri $Uri -TimeoutSec 3
      if($health.ok){ return $health }
    } catch {}
    Start-Sleep -Milliseconds 500
  }
  throw "$Name health check failed: $Uri"
}

$toolGateway=Join-Path $RepoRoot 'integrations\n8n\ck_nexus_dev_tool_gateway.mjs'
$groqAdapter=Join-Path $RepoRoot 'integrations\n8n\ck_nexus_groq_dev_adapter.mjs'
$sidecar=Join-Path $RepoRoot 'integrations\n8n\ck_nexus_agent_sidecar_v2.mjs'
$resourceEvidence=Join-Path $InstallRoot 'evidence\resource-guard-latest.json'
$checkpointDir=Join-Path $InstallRoot 'data\agnes-checkpoints-v2'
$logDir=Join-Path $InstallRoot 'logs'
$evidenceDir=Join-Path $InstallRoot 'evidence'

foreach($file in @($toolGateway,$groqAdapter,$sidecar,$GroqKeyFile)){
  if(!(Test-Path $file)){ throw "required runtime file not found: $file" }
}
foreach($port in @($ToolPort,$IntelligencePort,$SidecarPort)){ Assert-PortFree $port }

New-Item -ItemType Directory -Force -Path $logDir,$evidenceDir,$checkpointDir | Out-Null
$node=(Get-Command node.exe -ErrorAction Stop).Source
$toolToken=[guid]::NewGuid().ToString('N')
$intelligenceToken=[guid]::NewGuid().ToString('N')

$secure=Get-Content $GroqKeyFile | ConvertTo-SecureString
$bstr=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
  $groqKey=[Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
  if([string]::IsNullOrWhiteSpace($groqKey)){ throw 'Groq DPAPI credential decrypted to empty value' }

  $env:CK_NEXUS_TOOL_HOST='127.0.0.1'
  $env:CK_NEXUS_TOOL_PORT="$ToolPort"
  $env:CK_NEXUS_TOOL_TOKEN=$toolToken
  $env:CK_NEXUS_REPO_ROOT=$RepoRoot
  $tool=Start-Process -FilePath $node -ArgumentList @($toolGateway) -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $logDir 'agnes-tool-gateway.out.log') `
    -RedirectStandardError (Join-Path $logDir 'agnes-tool-gateway.err.log') -PassThru

  $env:GROQ_API_KEY=$groqKey
  $env:CK_NEXUS_GROQ_MODEL=$GroqModel
  $env:CK_NEXUS_INTELLIGENCE_HOST='127.0.0.1'
  $env:CK_NEXUS_INTELLIGENCE_PORT="$IntelligencePort"
  $env:CK_NEXUS_INTELLIGENCE_TOKEN=$intelligenceToken
  $groq=Start-Process -FilePath $node -ArgumentList @($groqAdapter) -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $logDir 'agnes-groq-adapter.out.log') `
    -RedirectStandardError (Join-Path $logDir 'agnes-groq-adapter.err.log') -PassThru
  Remove-Item Env:GROQ_API_KEY -ErrorAction SilentlyContinue

  $env:CK_NEXUS_SIDECAR_HOST='127.0.0.1'
  $env:CK_NEXUS_SIDECAR_PORT="$SidecarPort"
  $env:CK_NEXUS_TOOL_ENDPOINT="http://127.0.0.1:$ToolPort/v1/tool"
  $env:CK_NEXUS_TOOL_TOKEN=$toolToken
  $env:CK_NEXUS_INTELLIGENCE_ENDPOINT="http://127.0.0.1:$IntelligencePort/v1/intelligence"
  $env:CK_NEXUS_INTELLIGENCE_TOKEN=$intelligenceToken
  $env:CK_NEXUS_RESOURCE_EVIDENCE=$resourceEvidence
  $env:CK_NEXUS_CHECKPOINT_DIR=$checkpointDir
  $side=Start-Process -FilePath $node -ArgumentList @($sidecar) -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $logDir 'agnes-sidecar-v2.out.log') `
    -RedirectStandardError (Join-Path $logDir 'agnes-sidecar-v2.err.log') -PassThru
}
finally {
  if($bstr -ne [IntPtr]::Zero){ [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
  Remove-Variable groqKey -ErrorAction SilentlyContinue
  Remove-Item Env:GROQ_API_KEY -ErrorAction SilentlyContinue
}

$toolHealth=Wait-Health "http://127.0.0.1:$ToolPort/health" 'tool gateway'
$groqHealth=Wait-Health "http://127.0.0.1:$IntelligencePort/health" 'Groq adapter'
$sideHealth=Wait-Health "http://127.0.0.1:$SidecarPort/health" 'Sidecar v2'
if(-not $sideHealth.tool_token_configured){ throw 'Sidecar v2 tool token not configured' }
if(-not $sideHealth.upstream_configured){ throw 'Sidecar v2 intelligence upstream not configured' }

$commit=(git -C $RepoRoot rev-parse HEAD).Trim()
$tree=(git -C $RepoRoot rev-parse 'HEAD^{tree}').Trim()
$branch=(git -C $RepoRoot branch --show-current).Trim()
$clean=[string]::IsNullOrWhiteSpace((git -C $RepoRoot status --porcelain=v1 | Out-String).Trim())

$evidence=[ordered]@{
  schema_version='1.0'
  component='agnes-groq-development-stack'
  timestamp=(Get-Date).ToUniversalTime().ToString('o')
  mode='development_only'
  authority='ck_nexus_governor'
  provider='groq'
  model=$GroqModel
  branch=$branch
  commit=$commit
  tree=$tree
  clean=$clean
  tool_gateway=@{port=$ToolPort;pid=$tool.Id;ok=[bool]$toolHealth.ok}
  intelligence=@{port=$IntelligencePort;pid=$groq.Id;ok=[bool]$groqHealth.ok}
  sidecar=@{port=$SidecarPort;pid=$side.Id;ok=[bool]$sideHealth.ok;tool_token_configured=[bool]$sideHealth.tool_token_configured;upstream_configured=[bool]$sideHealth.upstream_configured}
  production_mutation=$false
  production_ready=$false
  q10_q11_q12_evidence=$false
}
$evidencePath=Join-Path $evidenceDir 'agnes-groq-runtime-startup-latest.json'
$evidence | ConvertTo-Json -Depth 6 | Set-Content -Path $evidencePath -Encoding UTF8
$evidence | ConvertTo-Json -Depth 6
