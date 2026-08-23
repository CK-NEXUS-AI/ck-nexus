param(
  [string]$RepoRoot='C:\CK-NEXUS\n8n-agent-worktree',
  [string]$InstallRoot='C:\CK-N8N',
  [string]$GroqKeyFile='C:\CK-N8N\secure\groq-api-key.dpapi',
  [string]$GroqModel='openai/gpt-oss-120b',
  [int]$ToolPort=8766,
  [int]$IntelligencePort=8767,
  [int]$SidecarPort=8776,
  [bool]$RequireClean=$true
)

$ErrorActionPreference='Stop'

function Get-EphemeralLoopbackPort {
  $listener=[System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback,0)
  try {
    $listener.Start()
    return ([System.Net.IPEndPoint]$listener.LocalEndpoint).Port
  }
  finally { $listener.Stop() }
}

function Resolve-DevelopmentPort([int]$Port) {
  $listener=Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
  if(-not $listener){ return $Port }
  $replacement=Get-EphemeralLoopbackPort
  Write-Verbose "development port $Port already in use; using ephemeral port $replacement"
  return $replacement
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

function Post-Json([string]$Uri,[hashtable]$Body,[hashtable]$Headers=@{}) {
  return Invoke-RestMethod -Uri $Uri -Method Post -Headers $Headers `
    -ContentType 'application/json' -Body ($Body | ConvertTo-Json -Depth 12 -Compress) -TimeoutSec 180
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

$commit=(git -C $RepoRoot rev-parse HEAD).Trim()
$tree=(git -C $RepoRoot rev-parse 'HEAD^{tree}').Trim()
$branch=(git -C $RepoRoot branch --show-current).Trim()
$statusText=(git -C $RepoRoot status --porcelain=v1 | Out-String).Trim()
$clean=[string]::IsNullOrWhiteSpace($statusText)
$allowedPrefix=@('post-p0/','dev/','feat/','fix/') | Where-Object { $branch.StartsWith($_) }
if(-not $allowedPrefix -or @('main','release/q10-q16-closure') -contains $branch){
  throw "development branch required; current branch: $branch"
}
if($RequireClean -and -not $clean){ throw 'exact-source startup requires a clean worktree' }

$ToolPort=Resolve-DevelopmentPort $ToolPort
$IntelligencePort=Resolve-DevelopmentPort $IntelligencePort
$SidecarPort=Resolve-DevelopmentPort $SidecarPort
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

$toolHeaders=@{'x-ck-nexus-tool-token'=$toolToken}
$toolProbe=Post-Json "http://127.0.0.1:$ToolPort/v1/tool" @{tool='repo_identity';args=@{}} $toolHeaders
if($toolProbe.identity.commit -ne $commit -or $toolProbe.identity.tree -ne $tree){
  throw 'Tool Gateway repository identity mismatch'
}
if($toolProbe.production_mutation -ne $false -or $toolProbe.raw_secret_access -ne $false){
  throw 'Tool Gateway safety labels invalid'
}

$protectedDenied=$false
try {
  Post-Json "http://127.0.0.1:$SidecarPort/v1/mission" @{
    branch='main';mission='protected-ref negative control';allow_production_mutation=$false;allow_secret_export=$false
  } | Out-Null
} catch {
  $code=$_.Exception.Response.StatusCode.value__
  if($code -eq 400){ $protectedDenied=$true }
}
if(-not $protectedDenied){ throw 'protected main negative control was not denied' }

$mission=Post-Json "http://127.0.0.1:$SidecarPort/v1/mission" @{
  branch=$branch
  mission='CK-NEXUS AGNES exact-source development runtime smoke test'
  allow_production_mutation=$false
  allow_secret_export=$false
}
if($mission.production_mutation_allowed -ne $false){ throw 'mission production boundary invalid' }

$agent=Post-Json "http://127.0.0.1:$SidecarPort/v1/agent" @{
  mission_id=$mission.mission_id
  branch=$branch
  phase='runtime_smoke'
  role='architect'
  skills=@('repo_architecture_analysis')
  prompt='Return final JSON confirming receipt of this development-only runtime smoke test. Do not request tools. Do not claim independent verification or production readiness.'
  allow_production_mutation=$false
  allow_secret_export=$false
}
if($agent.status -ne 'EXECUTED_UNVERIFIED'){ throw "unexpected agent status: $($agent.status)" }
if($agent.evidence_state -ne 'UNVERIFIED_UNTIL_INDEPENDENT_CHECK'){ throw 'agent evidence state invalid' }
if($agent.production_mutation_allowed -ne $false -or $agent.secret_export_allowed -ne $false){
  throw 'agent authority boundary invalid'
}

$evidence=[ordered]@{
  schema_version='1.1'
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
  tool_gateway=@{
    port=$ToolPort;pid=$tool.Id;ok=[bool]$toolHealth.ok
    repo_identity_verified=$true;read_only_probe='repo_identity'
  }
  intelligence=@{
    port=$IntelligencePort;pid=$groq.Id;ok=[bool]$groqHealth.ok
    e2e_status=$agent.status;evidence_state=$agent.evidence_state
  }
  sidecar=@{
    port=$SidecarPort;pid=$side.Id;ok=[bool]$sideHealth.ok
    tool_token_configured=[bool]$sideHealth.tool_token_configured
    upstream_configured=[bool]$sideHealth.upstream_configured
    protected_main_denied=$protectedDenied
    mission_id=$mission.mission_id
  }
  independent_verification='PENDING'
  production_mutation=$false
  production_ready=$false
  q10_q11_q12_evidence=$false
}
$evidencePath=Join-Path $evidenceDir 'agnes-groq-runtime-startup-latest.json'
$evidence | ConvertTo-Json -Depth 8 | Set-Content -Path $evidencePath -Encoding UTF8
$evidence | ConvertTo-Json -Depth 8
