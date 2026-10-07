param(
  [string]$InstallRoot='C:\CK-N8N',
  [int]$CriticalFreeMB=512,
  [int]$RedFreeMB=768,
  [int]$OrangeFreeMB=1280,
  [int]$YellowFreeMB=2048,
  [switch]$FailOnCritical
)
$ErrorActionPreference='Stop'
$os=Get-CimInstance Win32_OperatingSystem
$totalMB=[math]::Round($os.TotalVisibleMemorySize/1024,1)
$freeMB=[math]::Round($os.FreePhysicalMemory/1024,1)
$usedPct=[math]::Round((1-($freeMB/$totalMB))*100,1)
$page=Get-CimInstance Win32_PageFileUsage -ErrorAction SilentlyContinue
$pagefileConfigured=[bool]$page
$ck=Get-CimInstance Win32_Process | Where-Object {
  $_.CommandLine -match 'CK-N8N|ck_nexus_agent_sidecar|ck_nexus_dev_tool_gateway|ck_nexus_openai_dev_adapter'
}
$ckMB=[math]::Round((($ck | ForEach-Object { (Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue).WorkingSet64 } | Measure-Object -Sum).Sum/1MB),1)
if($freeMB -lt $CriticalFreeMB){$state='CRITICAL';$concurrency=0}
elseif($freeMB -lt $RedFreeMB){$state='RED';$concurrency=1}
elseif($freeMB -lt $OrangeFreeMB){$state='ORANGE';$concurrency=1}
elseif($freeMB -lt $YellowFreeMB){$state='YELLOW';$concurrency=2}
else{$state='GREEN';$concurrency=3}$result=[ordered]@{
  schema_version='1.0'
  component='ck-nexus-adaptive-resource-guard'
  mode='development_only'
  timestamp=(Get-Date).ToUniversalTime().ToString('o')
  total_memory_mb=$totalMB
  free_memory_mb=$freeMB
  used_memory_pct=$usedPct
  ck_runtime_working_set_mb=$ckMB
  pagefile_configured=$pagefileConfigured
  pressure_state=$state
  recommended_concurrency=$concurrency
  production_mutation=$false
}
$evidenceDir=Join-Path $InstallRoot 'evidence'
New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null
$evidenceFile=Join-Path $evidenceDir 'resource-guard-latest.json'
($result | ConvertTo-Json -Depth 4) | Set-Content -Path $evidenceFile -Encoding UTF8
$result | ConvertTo-Json -Depth 4
if($FailOnCritical -and $state -eq 'CRITICAL'){
  throw "CK-NEXUS resource guard blocked startup: free_memory_mb=$freeMB"
}