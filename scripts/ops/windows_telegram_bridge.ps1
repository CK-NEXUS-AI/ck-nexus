param([string]$Root = "C:\CK-NEXUS")

$ErrorActionPreference = "Stop"
$repo = Join-Path $Root "repo"
$python = Join-Path $repo ".venv\Scripts\python.exe"
$secretDir = Join-Path $Root "secrets"
$botTokenFile = Join-Path $secretDir "telegram_bot_token.txt"
$tokenMarker = Join-Path $secretDir "telegram_token_authorized.marker"
$allowedChatsFile = Join-Path $secretDir "telegram_allowed_chat_ids.txt"
$accessTokenFile = Join-Path $secretDir "access_token.txt"

foreach ($path in @($python, $botTokenFile, $accessTokenFile, $tokenMarker)) {
    if (-not (Test-Path $path)) { throw "Required runtime material missing: $path" }
}

$allowedChats = ""
if (Test-Path $allowedChatsFile) {
    $allowedChats = (Get-Content $allowedChatsFile -Raw).Trim()
}

$env:CKNEXUS_TELEGRAM_BOT_TOKEN = (Get-Content $botTokenFile -Raw).Trim()
$env:CKNEXUS_TELEGRAM_ALLOWED_CHAT_IDS = $allowedChats
$env:CKNEXUS_ACCESS_TOKEN = (Get-Content $accessTokenFile -Raw).Trim()
$env:CKNEXUS_API_BASE = "http://127.0.0.1:8000"
$env:CKNEXUS_TELEGRAM_AGENT_ID = "content-strategist"
Set-Location $repo
& $python -m creator_app.telegram_bridge
