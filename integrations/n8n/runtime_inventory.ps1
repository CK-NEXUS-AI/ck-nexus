param(
  [string]$InstallRoot = 'C:\CK-N8N',
  [string]$NodeRoot = 'C:\CKTools\node',
  [string]$AgentEndpoint = 'http://127.0.0.1:8765/v1/agent',
  [string]$N8nHealthUrl = 'http://127.0.0.1:5678/healthz'
)
$ErrorActionPreference = 'Stop'
function Safe-Run([scriptblock]$Block) {
  try { & $Block } catch { return "ERROR: $($_.Exception.Message)" }
}
$node = Join-Path $NodeRoot 'node.exe'
$npm = Join-Path $NodeRoot 'npm.cmd'
$n8n = Join-Path $InstallRoot 'node_modules\.bin\n8n.cmd'
$packageJson = Join-Path $InstallRoot 'package.json'
$result = [ordered]@{
  schema_version = '1.0'
  mode = 'development_only'
  authority = 'ck_nexus_governor'
  timestamp_utc = [DateTime]::UtcNow.ToString('o')
  host = $env:COMPUTERNAME
  node_present = Test-Path $node
  npm_present = Test-Path $npm
  n8n_present = Test-Path $n8n
  node_version = if (Test-Path $node) { Safe-Run { (& $node --version) -join "`n" } } else { $null }
  npm_version = if (Test-Path $npm) { Safe-Run { (& $npm --version) -join "`n" } } else { $null }
  n8n_version = if (Test-Path $n8n) { Safe-Run { (& $n8n --version) -join "`n" } } else { $null }
  package_dependencies = @{}
  n8n_processes = @()
  listen_5678 = $false
  listen_8765 = $false
  n8n_health = 'NOT_CHECKED'
  agent_endpoint = 'NOT_CHECKED'
  audit = 'NOT_RUN'
  production_ready = $false
  q10_q11_q12_evidence = $false
}
if (Test-Path $packageJson) {
  try {
    $pkg = Get-Content $packageJson -Raw | ConvertFrom-Json
    if ($pkg.dependencies) {
      foreach ($p in $pkg.dependencies.PSObject.Properties) { $result.package_dependencies[$p.Name] = $p.Value }
    }
  } catch { $result.package_dependencies = @{ error = $_.Exception.Message } }
}
$result.n8n_processes = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match '\bn8n\b' } | ForEach-Object { [ordered]@{ pid=$_.ProcessId; name=$_.Name; command_line=$_.CommandLine } })
try { $result.listen_5678 = [bool](Get-NetTCPConnection -State Listen -LocalPort 5678 -ErrorAction Stop) } catch {}
try { $result.listen_8765 = [bool](Get-NetTCPConnection -State Listen -LocalPort 8765 -ErrorAction Stop) } catch {}
try { $result.n8n_health = (Invoke-WebRequest -UseBasicParsing -Uri $N8nHealthUrl -TimeoutSec 5).StatusCode } catch { $result.n8n_health = "ERROR: $($_.Exception.Message)" }
try {
  $payload = @{ mission_id='inventory-probe'; request='runtime inventory connectivity probe'; branch='post-p0/n8n-development-agent-fabric'; role='verifier'; skills=@('repo_architecture_analysis'); authority='ck_nexus_governor'; allow_production_mutation=$false; allow_secret_export=$false } | ConvertTo-Json -Depth 5
  $resp = Invoke-WebRequest -UseBasicParsing -Uri $AgentEndpoint -Method POST -ContentType 'application/json' -Body $payload -TimeoutSec 10
  $result.agent_endpoint = $resp.StatusCode
} catch { $result.agent_endpoint = "ERROR: $($_.Exception.Message)" }
if (Test-Path $n8n) {
  $result.audit = Safe-Run { (& $n8n audit 2>&1) -join "`n" }
}
$result | ConvertTo-Json -Depth 8
