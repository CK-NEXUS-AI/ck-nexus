const streams = [
 {name:'Creator App · UI / API',weight:15,score:13,status:'Implemented; live AI mode not fully verified',evidence:'Existing responsive web app, API routes, Demo Mode and creator workflows.'},
 {name:'Control Plane / autonomous execution',weight:20,score:9,status:'Partially implemented',evidence:'Control-plane, execution-gate and OMNI issuer code/tests exist; production authority wiring is not enabled.'},
 {name:'Remote MCP security',weight:15,score:9,status:'Focused regression passed; deployment parity pending',evidence:'84 selected tests passed; service is loopback-only. Repo/deployed source parity remains unverified.'},
 {name:'CI / test automation',weight:15,score:8,status:'Mixed recent evidence',evidence:'GitHub Actions are present; 6 of the latest 10 runs succeeded and 4 failed.'},
 {name:'Integrations / developer tools',weight:10,score:5,status:'Partially connected',evidence:'GitHub CLI authenticated on VPS; n8n and MCP services exist, but end-to-end coverage is incomplete.'},
 {name:'Runtime operations / observability',weight:10,score:7,status:'Core services active',evidence:'Gateway, scanner, watchdog and MCP active at audit; disk usage is 81%.'},
 {name:'Model Studio / real inference',weight:5,score:1,status:'Not verified',evidence:'Endpoint is reachable, but authenticated inference has not been confirmed.'},
 {name:'Production security / release',weight:10,score:2,status:'Release gate remains closed',evidence:'Production NO-GO; end-to-end, independent security and rollback evidence still required.'}
];
const tools = [
 ['GH','Git + GitHub','Repository history, diff preservation, Issues and Actions.','Used',false],
 ['PY','Python 3.12','Runtime and automation scripts.','Used',false],
 ['PT','pytest','84 focused tests passed; full suite not claimed.','Verified',false],
 ['CI','GitHub Actions','Workflow evidence; recent results are mixed.','Mixed',true],
 ['DC','Desktop Commander','Authorized remote VPS shell and file inspection.','Used',false],
 ['OS','systemd / Linux','Service health and loopback listener checks.','Verified',false],
 ['MCP','MCP SDK / HTTP','Secure tool transport; private loopback binding.','Active',false],
 ['UV','uv / lockfile','Python dependency environment; lockfile needs review.','Review',true],
 ['DO','Docker','Container runtime present; no image cleanup performed.','Available',false],
 ['N8','n8n','Local service detected on loopback; workflows need audit.','Partial',true],
 ['OC','OpenClaw','Prior CLI/network timeout evidence; current inference not verified.','Pending',true],
 ['QW','Model Studio / Qwen','Protected endpoint config; no authenticated inference evidence.','Pending',true]
];
const total = streams.reduce((n,s)=>n+s.weight,0);
const earned = streams.reduce((n,s)=>n+s.score,0);
const percent = Math.round(earned / total * 100);
document.getElementById('overall-percent').innerHTML = `${percent}<span>%</span>`;
document.querySelector('.ring').style.background = `conic-gradient(var(--cyan) 0 ${percent}%,#24334a ${percent}% 100%)`;
document.querySelector('.ring').setAttribute('aria-label',`ความคืบหน้าประเมิน ${percent} เปอร์เซ็นต์`);
document.querySelector('.progress-notes h3').textContent = `${percent}% · ประเมินแบบถ่วงน้ำหนัก`;
document.getElementById('workstreams').innerHTML = streams.map(s=>`<article class="stream"><div class="stream-head"><strong>${s.name}</strong><span class="score">${s.score}<small> / ${s.weight} คะแนน</small></span></div><p>${s.evidence}</p><div class="bar" role="img" aria-label="${Math.round(s.score/s.weight*100)} เปอร์เซ็นต์ของ workstream"><span style="width:${Math.round(s.score/s.weight*100)}%"></span></div><div class="stream-foot"><span>${s.status}</span><span>น้ำหนัก ${s.weight}%</span></div></article>`).join('');
document.getElementById('tools-grid').innerHTML = tools.map(t=>`<article class="tool"><div class="tool-top"><span class="tool-mark">${t[0]}</span><span class="tool-status ${t[4]?'pending':''}">${t[3]}</span></div><h3>${t[1]}</h3><p>${t[2]}</p></article>`).join('');
