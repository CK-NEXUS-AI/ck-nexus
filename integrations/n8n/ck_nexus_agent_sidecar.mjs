import http from 'node:http';
import crypto from 'node:crypto';

const HOST = process.env.CK_NEXUS_SIDECAR_HOST || '127.0.0.1';
const PORT = Number(process.env.CK_NEXUS_SIDECAR_PORT || 8765);
const UPSTREAM = process.env.CK_NEXUS_INTELLIGENCE_ENDPOINT || '';
const UPSTREAM_TOKEN = process.env.CK_NEXUS_INTELLIGENCE_TOKEN || '';
const TOOL_ENDPOINT = process.env.CK_NEXUS_TOOL_ENDPOINT || 'http://127.0.0.1:8766/v1/tool';
const TOOL_TOKEN = process.env.CK_NEXUS_TOOL_TOKEN || '';
const MAX_TOOL_STEPS = Number(process.env.CK_NEXUS_MAX_TOOL_STEPS || 4);
const ALLOWED_PREFIXES = ['post-p0/', 'dev/', 'feat/', 'fix/'];
const DENIED_REFS = new Set(['main', 'release/q10-q16-closure']);
const ROLES = new Set([
  'orchestrator','researcher','architect','builder','test_engineer',
  'performance_engineer','ux_runtime_reviewer','verifier',
  'security_reviewer','evidence_auditor'
]);
const APPROVED_TOOLS = new Set([
  'repo_identity','git_status','git_diff_stat','read_tracked_file',
  'search_tracked_text','run_n8n_fabric_tests','run_n8n_fabric_ruff','run_test_file'
]);

function json(res, code, body) {
  const payload = JSON.stringify(body);
  res.writeHead(code, {'content-type':'application/json','cache-control':'no-store'});
  res.end(payload);
}

function allowedRef(ref) {
  if (!ref || DENIED_REFS.has(ref)) return false;
  return ALLOWED_PREFIXES.some((prefix) => ref.startsWith(prefix));
}

function assertSafe(input) {
  const branch = String(input.branch || '');
  if (!allowedRef(branch)) throw new Error('branch_not_allowed');
  if (input.allow_production_mutation === true) throw new Error('production_mutation_denied');
  if (input.allow_secret_export === true) throw new Error('secret_export_denied');
  if (Number(input.pull_request || 0) === 14) throw new Error('pr14_denied');
  return branch;
}

function missionEnvelope(input) {
  const branch = assertSafe(input);
  const mission = String(input.mission || input.request || '').trim();
  if (!mission) throw new Error('mission_required');
  return {
    mission_id: String(input.mission_id || `ckdev-${crypto.randomUUID()}`),
    mode: 'development_only', branch, mission,
    production_mutation_allowed: false, secret_read_allowed: false,
    merge_allowed: false, deploy_allowed: false, q10_promotion_allowed: false,
    evidence_state: 'UNVERIFIED_UNTIL_INDEPENDENT_CHECK'
  };
}

async function callTool(request) {
  const tool = String(request.tool || '');
  if (!APPROVED_TOOLS.has(tool)) throw new Error('tool_not_allowed');
  if (!TOOL_TOKEN) throw new Error('tool_token_not_configured');
  const response = await fetch(TOOL_ENDPOINT, {
    method:'POST',
    headers:{'content-type':'application/json','x-ck-nexus-tool-token':TOOL_TOKEN},
    body:JSON.stringify({tool,args:request.args || {}}),
    signal:AbortSignal.timeout(180000)
  });
  const text = await response.text();
  let body;
  try { body = JSON.parse(text); } catch { body = {output:text}; }
  if (!response.ok) throw new Error(`tool_${response.status}_${body.error || 'failed'}`);
  return body;
}

async function callUpstreamOnce(input, toolTrace) {
  const headers = {'content-type':'application/json','x-ck-nexus-mode':'development-only'};
  if (UPSTREAM_TOKEN) headers.authorization = `Bearer ${UPSTREAM_TOKEN}`;
  const response = await fetch(UPSTREAM, {
    method:'POST', headers,
    body:JSON.stringify({
      mission_id:input.mission_id, phase:input.phase, role:input.role,
      skills:input.skills || [], prompt:input.prompt, branch:input.branch,
      authority:'ck_nexus_governor', allow_production_mutation:false,
      allow_secret_export:false,
      tool_protocol:{
        allowed_tools:[...APPROVED_TOOLS], max_steps:MAX_TOOL_STEPS,
        request_shape:{type:'tool_request',tool:'repo_identity',args:{}},
        final_shape:{type:'final',result:'...',verdict:'PASS|FAIL|BLOCKED'}
      },
      tool_trace:toolTrace
    }), signal:AbortSignal.timeout(120000)
  });
  const text = await response.text();
  if (!response.ok) throw new Error(`upstream_${response.status}`);
  try { return JSON.parse(text); } catch { return {type:'final', result:{output:text}}; }
}

async function callUpstream(input) {
  if (!UPSTREAM) {
    return {status:'PROPOSAL_ONLY', reason:'intelligence_upstream_not_configured',
      role:input.role, skills:input.skills || [], evidence_state:'NOT_EXECUTED', tool_trace:[]};
  }
  const trace = [];
  for (let step = 0; step <= MAX_TOOL_STEPS; step += 1) {
    const result = await callUpstreamOnce(input, trace);
    const request = result?.type === 'tool_request' ? result : result?.tool_request;
    if (!request) {
      return {status:'EXECUTED_UNVERIFIED', role:input.role,
        result, tool_trace:trace, tool_steps:trace.length,
        evidence_state:'UNVERIFIED_UNTIL_INDEPENDENT_CHECK'};
    }
    if (step === MAX_TOOL_STEPS) throw new Error('tool_loop_limit');
    const toolResult = await callTool(request);
    trace.push({step:step + 1, tool:String(request.tool), args:request.args || {}, result:toolResult});
  }
  throw new Error('tool_loop_unreachable');
}

async function agentEnvelope(input) {
  const branch = assertSafe(input);
  const role = String(input.role || '');
  if (!ROLES.has(role)) throw new Error('role_not_allowed');
  const prompt = String(input.prompt || '').trim();
  if (!prompt) throw new Error('prompt_required');
  return {
    mission_id:String(input.mission_id || `ckdev-${crypto.randomUUID()}`),
    branch, phase:String(input.phase || 'candidate_generation'), role,
    skills:Array.isArray(input.skills) ? input.skills.map(String) : [],
    production_mutation_allowed:false, secret_export_allowed:false,
    ...(await callUpstream({...input, branch, role, prompt}))
  };
}

const server = http.createServer((req, res) => {
  if (req.method === 'GET' && req.url === '/health') {
    return json(res, 200, {ok:true, service:'ck-nexus-n8n-sidecar',
      mode:'development_only', upstream_configured:Boolean(UPSTREAM),
      tool_gateway:TOOL_ENDPOINT, tool_token_configured:Boolean(TOOL_TOKEN),
      max_tool_steps:MAX_TOOL_STEPS});
  }
  if (req.method !== 'POST' || !['/v1/mission','/v1/agent'].includes(req.url)) {
    return json(res, 404, {error:'not_found'});
  }
  let raw = '';
  req.on('data', (chunk) => { raw += chunk; if (raw.length > 262144) req.destroy(); });
  req.on('end', async () => {
    try {
      const input = JSON.parse(raw || '{}');
      const body = req.url === '/v1/mission' ? missionEnvelope(input) : await agentEnvelope(input);
      return json(res, req.url === '/v1/mission' ? 202 : 200, body);
    } catch (error) {
      return json(res, 400, {error:String(error.message || error), mode:'fail_closed'});
    }
  });
});

server.listen(PORT, HOST, () => {
  console.log(`CK-NEXUS n8n sidecar listening on http://${HOST}:${PORT}`);
});
