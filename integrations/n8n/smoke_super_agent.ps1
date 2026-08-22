param([string]$BaseUrl='http://127.0.0.1:8765')
$ErrorActionPreference='Stop'

Write-Host '=== HEALTH ==='
$health=Invoke-RestMethod -Uri "$BaseUrl/health" -TimeoutSec 5
if (-not $health.ok) { throw 'health failed' }
$health | ConvertTo-Json -Compress | Write-Host

Write-Host '=== PROTECTED REF MUST DENY ==='
$denied=$false
try {
  Invoke-RestMethod -Method Post -Uri "$BaseUrl/v1/mission" -ContentType 'application/json' -Body (@{
    mission='should be denied'; branch='main'
  } | ConvertTo-Json) -TimeoutSec 5 | Out-Null
} catch {
  if ($_.Exception.Response.StatusCode.value__ -eq 400) { $denied=$true }
}
if (-not $denied) { throw 'main branch was not denied' }
Write-Host 'PASS: main denied'

Write-Host '=== DEVELOPMENT MISSION ==='
$mission=Invoke-RestMethod -Method Post -Uri "$BaseUrl/v1/mission" -ContentType 'application/json' -Body (@{
  mission='Analyze CK-NEXUS development architecture'; branch='post-p0/n8n-super-agent-smoke'
} | ConvertTo-Json) -TimeoutSec 5
if ($mission.mode -ne 'development_only') { throw 'mode mismatch' }
if ($mission.production_mutation_allowed) { throw 'production mutation unexpectedly allowed' }
Write-Host ($mission | ConvertTo-Json -Compress)

Write-Host '=== SPECIALIST CALL ==='
$agent=Invoke-RestMethod -Method Post -Uri "$BaseUrl/v1/agent" -ContentType 'application/json' -Body (@{
  mission_id=$mission.mission_id; phase='candidate_generation'; role='architect';
  skills=@('repo_architecture_analysis','api_contract_review');
  prompt='Review development architecture and return a proposal only.';
  branch='post-p0/n8n-super-agent-smoke'; allow_production_mutation=$false; allow_secret_export=$false
} | ConvertTo-Json) -TimeoutSec 10
if ($agent.production_mutation_allowed) { throw 'agent mutation unexpectedly allowed' }
if ($agent.status -notin @('PROPOSAL_ONLY','EXECUTED_UNVERIFIED')) { throw "unexpected agent status: $($agent.status)" }
Write-Host ($agent | ConvertTo-Json -Compress)
Write-Host 'CK-NEXUS SUPER-AGENT LOCAL SMOKE PASS'
