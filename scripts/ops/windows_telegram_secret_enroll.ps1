param([string]$Root = "C:\CK-NEXUS")

$ErrorActionPreference = "Stop"
$secretDir = Join-Path $Root "secrets"
$tokenFile = Join-Path $secretDir "telegram_bot_token.txt"
$markerFile = Join-Path $secretDir "telegram_token_authorized.marker"
New-Item -ItemType Directory -Force -Path $secretDir | Out-Null
Remove-Item $markerFile -Force -ErrorAction SilentlyContinue

$secure = Read-Host "Paste NEW BotFather token" -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
    $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    if ([string]::IsNullOrWhiteSpace($plain)) { throw "Token cannot be empty" }
    $token = $plain.Trim()
    if ($token -match "\s") { throw "Token must not contain whitespace" }
    Set-Content -Path $tokenFile -Value $token -NoNewline -Encoding ascii
    $me = Invoke-RestMethod ("https://api.telegram.org/bot" + $token + "/getMe") -TimeoutSec 15
    if (-not $me.ok) { throw "Telegram getMe verification failed" }
    Set-Content -Path $markerFile -Value "verified" -NoNewline -Encoding ascii
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    Remove-Variable plain,token -ErrorAction SilentlyContinue
}

icacls $secretDir /inheritance:r /grant "Administrators:(OI)(CI)F" /grant "SYSTEM:(OI)(CI)F" | Out-Null
Write-Output "TELEGRAM_TOKEN=VERIFIED_AND_AUTHORIZED"
Start-ScheduledTask -TaskName "CK-NEXUS-TelegramBridge" -ErrorAction SilentlyContinue
