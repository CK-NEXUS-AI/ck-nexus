param(
  [string]$BaseUrl='http://127.0.0.1:8765',
  [string]$ToolUrl='http://127.0.0.1:8766'
)
$ErrorActionPreference='Stop'

Write-Host '=== SIDECAR HEALTH ==='
$health=Invoke-RestMethod -Uri "$BaseUrl/health" -TimeoutSec 5
if (-not $health.ok) { throw 'sidecar health failed' }
$health | ConvertTo-Json -Compress | Write-Host

Write-Host '=== TOOL GATEWAY HEALTH ==='
$toolHealth=Invoke-RestMethod -Uri "$ToolUrl/health" -TimeoutSec 5
if (-not $toolHealth.ok) { throw 'tool gateway health failed' }
if (-not $toolHealth.token_required) { throw 'tool gateway token is not required' }

Write-Host '=== TOOL CALL WITHOUT TOKEN MUST DENY ==='
$toolDenied=$false
try {
  Invoke-RestMethod -Method Post -Uri "$ToolUrl/v1/tool" -ContentType 'application/json' -Body (@{tool='repo_identity';args=@{}} | ConvertTo-Json) -TimeoutSec 5 | Out-Null
} catch {
  if ($_.Exception.Response.StatusCode.value__ -eq 401) { $toolDenied=$true }
}
if (-not $toolDenied) { throw 'tool gateway accepted unauthenticated request' }
Write-Host 'PASS: unauthenticated tool call denied'

if (-not $env:CK_NEXUS_TOOL_TOKEN) { throw 'CK_NEXUS_TOOL_TOKEN missing from smoke process' }
Write-Host '=== AUTHENTICATED REPO IDENTITY ==='
$toolHeaders=@{'X-CK-NEXUS-Tool-Token'=$env:CK_NEXUS_TOOL_TOKEN}
$identity=Invoke-RestMethod -Method Post -Uri "$ToolUrl/v1/tool" -Headers $toolHeaders -ContentType 'application/json' -Body (@{tool='repo_identity';args=@{}} | ConvertTo-Json) -TimeoutSec 10
if ($identity.identity.branch -notmatch '^(post-p0|feat|fix|dev)/') { throw "unexpected branch: $($identity.identity.branch)" }
if ($identity.production_mutation) { throw 'tool gateway mutation unexpectedly allowed' }
Write-Host ($identity | ConvertTo-Json -Compress)

Write-Host '=== PROTECTED REF MUST DENY ==='
$denied=$false
try {
  Invoke-RestMethod -Method Post -Uri "$BaseUrl/v1/mission" -ContentType 'application/json' -Body (@{mission='should be denied';branch='main'} | ConvertTo-Json) -TimeoutSec 5 | Out-Null
} catch {
  if ($_.Exception.Response.StatusCode.value__ -eq 400) { $denied=$true }
}
if (-not $denied) { throw 'main branch was not denied' }
Write-Host 'PASS: main denied'

Write-Host '=== DEVELOPMENT MISSION ==='
$mission=Invoke-RestMethod -Method Post -Uri "$BaseUrl/v1/mission" -ContentType 'application/json' -Body (@{mission='Analyze CK-NEXUS development architecture';branch='post-p0/n8n-super-agent-smoke'} | ConvertTo-Json) -TimeoutSec 5
if ($mission.mode -ne 'development_only') { throw 'mode mismatch' }
if ($mission.production_mutation_allowed) { throw 'production mutation unexpectedly allowed' }

Write-Host '=== SPECIALIST CALL ==='
$agent=Invoke-RestMethod -Method Post -Uri "$BaseUrl/v1/agent" -ContentType 'application/json' -Body (@{
  mission_id=$mission.mission_id; phase='candidate_generation'; role='architect';
  skills=@('repo_architecture_analysis','api_contract_review');
  prompt='Review development architecture and return a proposal only.';
  branch='post-p0/n8n-super-agent-smoke'; allow_production_mutation=$false; allow_secret_export=$false
} | ConvertTo-Json) -TimeoutSec 15
if ($agent.production_mutation_allowed) { throw 'agent mutation unexpectedly allowed' }
if ($agent.status -notin @('PROPOSAL_ONLY','EXECUTED_UNVERIFIED')) { throw "unexpected agent status: $($agent.status)" }
Write-Host ($agent | ConvertTo-Json -Compress)
Write-Host 'CK-NEXUS SUPER-AGENT LOCAL SMOKE PASS'
