const streams = [
 {name:'Creator Edition · UI / API',status:'Implemented; Live Mode unverified',evidence:'Responsive Thai UI, 4 Creator Agents, Demo Mode, provider routing, SQLite history and status APIs exist. No authenticated live inference evidence yet.'},
 {name:'Control Plane / autonomous execution',status:'Implemented in bounded development scope',evidence:'Task Store, Worker, verification and safe-canary path exist. General autonomous execution and production authority remain fail-closed.'},
 {name:'MCP Service / deployment',status:'Active · loopback-only',evidence:'Read-only VPS check confirms cknexus-mcp.service active and listener 127.0.0.1:8765. Repository/deployed-source parity has not been certified.'},
 {name:'SQLite replay protection',status:'Merged · PR #332',evidence:'Squash merge commit 43cb6f09b213b00700b165562da51c3ee508641a; required CI, preflight, attack regression, CodeQL and reviewer checks passed.'},
 {name:'Dependency audit · PR #331 / Issue #317',status:'Merged · Issue closed',evidence:'Squash merge commit 1355e5250d08d2041bc80cd0e5867b4b8848b9e4; test and verify-image passed after rebase. VPS pip-audit found no known vulnerabilities; local package ck-nexus-creator is not on PyPI and was not audited.'},
 {name:'AGNES Phase 2 / Phase 3',status:'Merged · PR #334',evidence:'Squash merge commit 0fb3a14b052c903d75e971d0fa463b6e83834e44. Clean main after merge: full suite 927 passed, 2 skipped, 25 warnings; targeted Phase 2/3 21 passed. No tests were skipped to hide the original failures.'},
 {name:'Runtime operations / disk',status:'Services active; disk watch required',evidence:'Gateway, scanner, MCP and watchdog timer active on VPS. Root filesystem 81% used, 7.6 GB free after apt/uv/pycache cleanup; recovery drill is not verified.'},
 {name:'Model Studio / Qwen inference',status:'Authenticated inference PASS',evidence:'VPS request using DASHSCOPE_API_KEY from the service environment returned HTTP 200, a non-empty model response and usage metadata in 4.38 seconds. Secret value was not printed. This proves inference only, not production readiness.'},
 {name:'Security / Q10–Q16 / Production',status:'NOT VERIFIED · NO-GO',evidence:'Requires gate-specific evidence, independent human review, deployment/end-to-end and rollback verification, plus Owner sign-off.'}
];
const container = document.getElementById('workstreams');
container.innerHTML = streams.map(s=>`<article class="stream"><div class="stream-head"><strong>${s.name}</strong><span class="tool-status pending">${s.status}</span></div><p>${s.evidence}</p></article>`).join('');
