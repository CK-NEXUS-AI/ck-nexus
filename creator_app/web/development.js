const streams = [
 {name:'Creator Edition · UI / API',status:'Implemented; Live Mode unverified',evidence:'Responsive Thai UI, 4 Creator Agents, Demo Mode, provider routing, SQLite history and status APIs exist. No authenticated live inference evidence yet.'},
 {name:'Control Plane / autonomous execution',status:'Implemented in bounded development scope',evidence:'Task Store, Worker, verification and safe-canary path exist. General autonomous execution and production authority remain fail-closed.'},
 {name:'MCP Service / deployment',status:'Active · loopback-only',evidence:'Read-only VPS check confirms cknexus-mcp.service active and listener 127.0.0.1:8765. Repository/deployed-source parity has not been certified.'},
 {name:'SQLite replay protection',status:'Fix under review · PR #332',evidence:'PR checks pass for test (906 passed, 2 skipped; Phase 2/3 excluded), preflight, attack regression, JS/Python analysis and Cubic. Open, not merged.'},
 {name:'Dependency audit · PR #331',status:'Blocked by CI failures',evidence:'VPS pip-audit reported no known vulnerabilities for the checked environment; GitHub Portable regression and verify-image failed. Draft remains unmerged.'},
 {name:'AGNES Phase 2 / Phase 3',status:'Needs failure isolation',evidence:'Local full test run had 7 failures in namespace/sandbox and candidate pipeline tests. Do not assume environment-only without base-vs-branch evidence.'},
 {name:'Runtime operations / disk',status:'Services active; disk watch required',evidence:'Gateway, scanner, MCP and watchdog timer active on VPS. Root filesystem 81% used, 7.8 GB free; recovery drill is not verified.'},
 {name:'Model Studio / Qwen inference',status:'Not verified',evidence:'No confirmed authenticated request/response. Do not claim live inference is working.'},
 {name:'Security / Q10–Q16 / Production',status:'NOT VERIFIED · NO-GO',evidence:'Requires gate-specific evidence, independent human review, deployment/end-to-end and rollback verification, plus Owner sign-off.'}
];
const container = document.getElementById('workstreams');
container.innerHTML = streams.map(s=>`<article class="stream"><div class="stream-head"><strong>${s.name}</strong><span class="tool-status pending">${s.status}</span></div><p>${s.evidence}</p></article>`).join('');
