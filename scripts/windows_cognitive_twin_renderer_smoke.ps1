param(
    [Parameter(Mandatory = $true)]
    [string]$WebRoot,

    [string]$NodePath = "C:\CKTools\node\node.exe",

    [string]$EdgePath = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
)

$ErrorActionPreference = "Stop"

$renderer = Join-Path $WebRoot "cognitive-twin-renderer.js"
if (-not (Test-Path -LiteralPath $renderer)) {
    throw "Renderer not found: $renderer"
}
if (-not (Test-Path -LiteralPath $NodePath)) {
    throw "Node not found: $NodePath"
}
if (-not (Test-Path -LiteralPath $EdgePath)) {
    throw "Edge not found: $EdgePath"
}

& $NodePath --check $renderer
if ($LASTEXITCODE -ne 0) {
    throw "Renderer JavaScript syntax check failed"
}

$smokePath = Join-Path $WebRoot "renderer-smoke.html"
$html = @'
<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>CK-NEXUS renderer smoke</title></head>
<body>
  <div id="scene">renderer smoke</div>
  <script src="./cognitive-twin-renderer.js"></script>
  <script>
    window.addEventListener("load", () => {
      window.dispatchEvent(new CustomEvent("cknexus:projected-state", {
        detail: {
          agent_id: "verifier",
          state: "executing",
          truth_class: "VERIFIED",
          verified: false,
          evidence_id: "EVD-SMOKE"
        }
      }));
      const scene = document.getElementById("scene");
      const pass = scene.dataset.renderer === "css-fallback"
        && scene.dataset.projectedAgent === "verifier"
        && scene.dataset.projectedMotion === "executing"
        && scene.dataset.projectedTruth === "OBSERVED"
        && scene.dataset.projectedVerified === "false";
      document.body.dataset.smoke = pass ? "PASS" : "FAIL";
    });
  </script>
</body>
</html>
'@
Set-Content -LiteralPath $smokePath -Value $html -Encoding UTF8

$uri = (New-Object System.Uri($smokePath)).AbsoluteUri
$dump = & $EdgePath --headless --disable-gpu --no-first-run --no-default-browser-check --virtual-time-budget=2000 --dump-dom $uri 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "Edge headless smoke failed to execute"
}
if ($dump -notmatch 'data-smoke="PASS"') {
    throw "Renderer browser smoke did not reach PASS"
}

Write-Output "WINDOWS_RENDERER_SMOKE_PASS"
