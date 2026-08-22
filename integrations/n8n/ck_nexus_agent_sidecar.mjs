import http from 'node:http';
import crypto from 'node:crypto';

const HOST = process.env.CK_NEXUS_SIDECAR_HOST || '127.0.0.1';
const PORT = Number(process.env.CK_NEXUS_SIDECAR_PORT || 8765);
const UPSTREAM = process.env.CK_NEXUS_INTELLIGENCE_ENDPOINT || '';
const UPSTREAM_TOKEN = process.env.CK_NEXUS_INTELLIGENCE_TOKEN || '';
const ALLOWED_PREFIXES = ['post-p0/', 'dev/', 'feat/', 'fix/'];
const DENIED_REFS = new Set(['main', 'release/q10-q16-closure']);
const ROLES = new Set([
  'orchestrator','researcher','architect','builder','test_engineer',
  'performance_engineer','ux_runtime_reviewer','verifier',
  'security_reviewer','evidence_auditor'
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

async function callUpstream(input) {
  if (!UPSTREAM) {
    return {status:'PROPOSAL_ONLY', reason:'intelligence_upstream_not_configured',
      role:input.role, skills:input.skills || [], evidence_state:'NOT_EXECUTED'};
  }
  const headers = {'content-type':'application/json','x-ck-nexus-mode':'development-only'};
  if (UPSTREAM_TOKEN) headers.authorization = `Bearer ${UPSTREAM_TOKEN}`;
  const response = await fetch(UPSTREAM, {
    method:'POST', headers,
    body:JSON.stringify({
      mission_id:input.mission_id, phase:input.phase, role:input.role,
      skills:input.skills || [], prompt:input.prompt, branch:input.branch,
      authority:'ck_nexus_governor', allow_production_mutation:false,
      allow_secret_export:false
    }), signal:AbortSignal.timeout(120000)
  });
  const text = await response.text();
  if (!response.ok) throw new Error(`upstream_${response.status}`);
  let result;
  try { result = JSON.parse(text); } catch { result = {output:text}; }
  return {status:'EXECUTED_UNVERIFIED', role:input.role,
    upstream_status:response.status, result,
    evidence_state:'UNVERIFIED_UNTIL_INDEPENDENT_CHECK'};
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
      mode:'development_only', upstream_configured:Boolean(UPSTREAM)});
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
