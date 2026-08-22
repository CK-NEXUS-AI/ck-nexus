import http from 'node:http';
import crypto from 'node:crypto';

const HOST = process.env.CK_NEXUS_SIDECAR_HOST || '127.0.0.1';
const PORT = Number(process.env.CK_NEXUS_SIDECAR_PORT || 8765);
const ALLOWED_PREFIXES = ['post-p0/', 'dev/', 'feat/'];
const DENIED_REFS = new Set(['main', 'release/q10-q16-closure']);
const ROLES = ['orchestrator','researcher','architect','builder','verifier','security_reviewer'];

function json(res, code, body) {
  const payload = JSON.stringify(body);
  res.writeHead(code, {'content-type':'application/json','cache-control':'no-store'});
  res.end(payload);
}

function allowedRef(ref) {
  if (!ref || DENIED_REFS.has(ref)) return false;
  return ALLOWED_PREFIXES.some((prefix) => ref.startsWith(prefix));
}

function missionEnvelope(input) {
  const branch = String(input.branch || '');
  if (!allowedRef(branch)) throw new Error('branch_not_allowed');
  const mission = String(input.mission || '').trim();
  if (!mission) throw new Error('mission_required');
  const missionId = `ckdev-${crypto.randomUUID()}`;
  return {
    mission_id: missionId,
    mode: 'development_only',
    branch,
    production_mutation_allowed: false,
    secret_read_allowed: false,
    merge_allowed: false,
    deploy_allowed: false,
    q10_promotion_allowed: false,
    roles: ROLES.map((role) => ({role, status: 'PROPOSED'})),
    mission,
    evidence_state: 'UNVERIFIED_UNTIL_INDEPENDENT_CHECK'
  };
}

const server = http.createServer((req, res) => {
  if (req.method === 'GET' && req.url === '/health') {
    return json(res, 200, {ok:true, service:'ck-nexus-n8n-sidecar', mode:'development_only'});
  }
  if (req.method !== 'POST' || req.url !== '/v1/mission') {
    return json(res, 404, {error:'not_found'});
  }
  let raw = '';
  req.on('data', (chunk) => { raw += chunk; if (raw.length > 65536) req.destroy(); });
  req.on('end', () => {
    try {
      const input = JSON.parse(raw || '{}');
      return json(res, 202, missionEnvelope(input));
    } catch (error) {
      return json(res, 400, {error:String(error.message || error), mode:'fail_closed'});
    }
  });
});

server.listen(PORT, HOST, () => {
  console.log(`CK-NEXUS n8n sidecar listening on http://${HOST}:${PORT}`);
});
