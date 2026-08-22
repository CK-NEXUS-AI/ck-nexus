import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const REGISTRY_URL = new URL('./agnes-fabric-registry.json', import.meta.url);
const REGISTRY = JSON.parse(fs.readFileSync(REGISTRY_URL, 'utf8'));
const CHECKPOINT_DIR = path.resolve(
  process.env.CK_NEXUS_CHECKPOINT_DIR || path.join(process.cwd(), '.ck-nexus-checkpoints')
);
const RESOURCE_EVIDENCE = process.env.CK_NEXUS_RESOURCE_EVIDENCE || '';

function tokenize(value) {
  return String(value || '').toLowerCase().split(/[^\p{L}\p{N}_-]+/u).filter(Boolean);
}

function readResourceEvidence() {
  try {
    if (!RESOURCE_EVIDENCE || !fs.existsSync(RESOURCE_EVIDENCE)) return null;
    return JSON.parse(fs.readFileSync(RESOURCE_EVIDENCE, 'utf8').replace(/^\uFEFF/, ''));
  } catch {
    return null;
  }
}

function scoreCapability(capability, tokens) {
  const words = new Set((capability.keywords || []).flatMap(tokenize));
  let score = 0;
  for (const token of tokens) if (words.has(token)) score += 1;
  return score;
}
export function selectCapabilities(input = {}) {
  const tokens = tokenize([input.mission, input.prompt, input.role, ...(input.skills || [])].join(' '));
  const ranked = REGISTRY.capabilities
    .map((capability) => ({...capability, score:scoreCapability(capability, tokens)}))
    .filter((capability) => capability.score > 0)
    .sort((a, b) => b.score - a.score || a.id.localeCompare(b.id));
  const active = ranked.filter((item) => item.status === 'active').slice(0, 5);
  const contractOnly = ranked.filter((item) => item.status === 'contract_only').slice(0, 5);
  if (!active.length) {
    active.push(...REGISTRY.capabilities.filter((item) => item.status === 'active').slice(0, 3));
  }
  return {
    active:active.map(({id, risk, score}) => ({id, risk, score})),
    contract_only:contractOnly.map(({id, risk, score}) => ({id, risk, score}))
  };
}

export function resourceAdmission(input = {}) {
  const evidence = input.resource_state || readResourceEvidence() || {};
  const pressure = String(evidence.pressure_state || 'UNKNOWN').toUpperCase();
  const fallback = {max_concurrency:1, max_tool_steps:2};
  const policy = REGISTRY.pressure_policy[pressure] || fallback;
  const requested = {...REGISTRY.resource_defaults, ...(input.resource_contract || {})};
  const maxConcurrency = Math.min(Number(requested.max_concurrency || 1), policy.max_concurrency);
  const maxToolSteps = Math.min(Number(requested.max_tool_steps || 1), policy.max_tool_steps);
  const decision = pressure === 'CRITICAL' || maxConcurrency < 1 ? 'DENY' :
    ['RED','ORANGE'].includes(pressure) ? 'DEGRADE' : pressure === 'UNKNOWN' ? 'DEGRADE' : 'ALLOW';
  return {
    decision,
    pressure_state:pressure,
    max_concurrency:maxConcurrency,
    max_tool_steps:maxToolSteps,
    allow_browser:Boolean(requested.allow_browser) && ['GREEN','YELLOW'].includes(pressure),
    allow_large_binary:Boolean(requested.allow_large_binary) && pressure === 'GREEN',
    hibernatable:requested.hibernatable !== false,
    evidence:{
      free_memory_mb:evidence.free_memory_mb ?? null,
      used_memory_pct:evidence.used_memory_pct ?? null,
      pagefile_configured:evidence.pagefile_configured ?? null
    }
  };
}

export function traceEnvelope(input = {}) {
  return {
    trace_id:String(input.trace_id || crypto.randomUUID()),
    span_id:crypto.randomBytes(8).toString('hex'),
    mission_id:String(input.mission_id || ''),
    task_id:String(input.task_id || ''),
    agent_id:String(input.agent_id || input.role || ''),
    role:String(input.role || ''),
    branch:String(input.branch || ''),
    authority:'ck_nexus_governor',
    timestamp:new Date().toISOString(),
    production_mutation:false,
    evidence_state:'UNVERIFIED_UNTIL_INDEPENDENT_CHECK'
  };
}
function safeCheckpointId(value) {
  const id = String(value || '').trim();
  if (!/^[A-Za-z0-9._:-]{8,160}$/.test(id)) throw new Error('invalid_checkpoint_id');
  return id;
}

export function checkpointEnvelope(input = {}) {
  const missionId = safeCheckpointId(input.mission_id || `ckdev-${crypto.randomUUID()}`);
  return {
    schema_version:'1.0',
    checkpoint_id:String(input.checkpoint_id || `${missionId}:${Date.now()}`),
    mission_id:missionId,
    branch:String(input.branch || ''),
    phase:String(input.phase || 'candidate_generation'),
    completed_roles:Array.isArray(input.completed_roles) ? input.completed_roles.map(String) : [],
    pending_roles:Array.isArray(input.pending_roles) ? input.pending_roles.map(String) : [],
    artifacts:Array.isArray(input.artifacts) ? input.artifacts : [],
    evidence_state:String(input.evidence_state || 'UNVERIFIED_UNTIL_INDEPENDENT_CHECK'),
    next_action:String(input.next_action || ''),
    updated_at:new Date().toISOString(),
    production_mutation:false
  };
}

export function saveCheckpoint(input = {}) {
  const checkpoint = checkpointEnvelope(input);
  fs.mkdirSync(CHECKPOINT_DIR, {recursive:true});
  const id = safeCheckpointId(checkpoint.mission_id);
  const target = path.join(CHECKPOINT_DIR, `${id}.json`);
  const temp = `${target}.${crypto.randomUUID()}.tmp`;
  fs.writeFileSync(temp, JSON.stringify(checkpoint, null, 2), {encoding:'utf8', flag:'wx'});
  fs.renameSync(temp, target);
  return checkpoint;
}

export function loadCheckpoint(missionId) {
  const id = safeCheckpointId(missionId);
  const target = path.join(CHECKPOINT_DIR, `${id}.json`);
  if (!fs.existsSync(target)) throw new Error('checkpoint_not_found');
  return JSON.parse(fs.readFileSync(target, 'utf8').replace(/^\uFEFF/, ''));
}

export function buildAgnesContext(input = {}) {
  const capabilities = selectCapabilities(input);
  const resource_decision = resourceAdmission(input);
  const trace = traceEnvelope(input);
  return {
    fabric:'AGNES Cognitive Execution Fabric',
    authority:'ck_nexus_governor',
    mode:'development_only',
    capabilities,
    resource_decision,
    trace,
    agent_modes:REGISTRY.agent_modes,
    protocols:REGISTRY.protocols.map(({id,status}) => ({id,status})),
    memory_layers:REGISTRY.memory_layers,
    production_mutation:false
  };
}

export function fabricHealth() {
  return {
    ok:true,
    schema_version:REGISTRY.schema_version,
    active_capabilities:REGISTRY.capabilities.filter((item) => item.status === 'active').length,
    contract_only_capabilities:REGISTRY.capabilities.filter((item) => item.status === 'contract_only').length,
    checkpoint_dir:CHECKPOINT_DIR,
    resource_evidence_configured:Boolean(RESOURCE_EVIDENCE),
    production_mutation:false
  };
}
