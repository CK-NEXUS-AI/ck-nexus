import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';
import { spawn } from 'node:child_process';

const HOST = process.env.CK_NEXUS_TOOL_HOST || '127.0.0.1';
const PORT = Number(process.env.CK_NEXUS_TOOL_PORT || 8766);
const REPO = path.resolve(process.env.CK_NEXUS_REPO_ROOT || process.cwd());
const GIT = process.env.CK_NEXUS_GIT || 'git';
const UV = process.env.CK_NEXUS_UV || 'uv';
const ALLOWED_PREFIXES = ['post-p0/', 'dev/', 'feat/', 'fix/'];
const PROTECTED = new Set(['main', 'release/q10-q16-closure']);
const MAX_OUTPUT = 512 * 1024;
const MAX_FILE = 256 * 1024;

function respond(res, code, body) {
  res.writeHead(code, {'content-type':'application/json','cache-control':'no-store'});
  res.end(JSON.stringify(body));
}

function run(exe, args, timeoutMs = 120000) {
  return new Promise((resolve, reject) => {
    const child = spawn(exe, args, {cwd:REPO, windowsHide:true, shell:false});
    let stdout = '', stderr = '', killed = false;
    const timer = setTimeout(() => { killed = true; child.kill(); }, timeoutMs);
    child.stdout.on('data', d => { if (stdout.length < MAX_OUTPUT) stdout += d.toString(); });
    child.stderr.on('data', d => { if (stderr.length < MAX_OUTPUT) stderr += d.toString(); });
    child.on('error', err => { clearTimeout(timer); reject(err); });
    child.on('close', code => {
      clearTimeout(timer);
      if (killed) return reject(new Error('tool_timeout'));
      resolve({code, stdout:stdout.slice(0,MAX_OUTPUT), stderr:stderr.slice(0,MAX_OUTPUT)});
    });
  });
}

async function currentBranch() {
  const r = await run(GIT, ['branch','--show-current'], 10000);
  if (r.code !== 0) throw new Error('git_branch_failed');
  return r.stdout.trim();
}

function branchAllowed(branch) {
  return Boolean(branch) && !PROTECTED.has(branch) && ALLOWED_PREFIXES.some(p => branch.startsWith(p));
}

function safeRelative(input) {
  const rel = String(input || '').replaceAll('\\','/');
  if (!rel || rel.startsWith('/') || rel.includes('../') || rel.includes('/../')) throw new Error('invalid_path');
  if (rel === '.env' || rel.startsWith('.env.') || rel.startsWith('.git/')) throw new Error('sensitive_path_denied');
  return rel;
}

async function ensureTracked(rel) {
  const r = await run(GIT, ['ls-files','--error-unmatch','--',rel], 10000);
  if (r.code !== 0) throw new Error('tracked_file_required');
}

async function identity() {
  const [commit, tree, status, branch] = await Promise.all([
    run(GIT, ['rev-parse','HEAD'], 10000),
    run(GIT, ['rev-parse','HEAD^{tree}'], 10000),
    run(GIT, ['status','--porcelain=v1'], 10000),
    currentBranch()
  ]);
  return {
    branch,
    commit:commit.stdout.trim(),
    tree:tree.stdout.trim(),
    clean:status.stdout.trim() === '',
    status:status.stdout.trim().split(/\r?\n/).filter(Boolean).slice(0,200)
  };
}

async function executeTool(input) {
  const id = await identity();
  if (!branchAllowed(id.branch)) throw new Error('development_branch_required');
  const tool = String(input.tool || '');
  const args = input.args && typeof input.args === 'object' ? input.args : {};
  if (tool === 'repo_identity') return {tool, identity:id};
  if (tool === 'git_status') {
    const r = await run(GIT, ['status','--short','--branch'], 10000);
    return {tool, identity:id, exit_code:r.code, output:r.stdout, error:r.stderr};
  }
  if (tool === 'git_diff_stat') {
    const r = await run(GIT, ['diff','--stat'], 10000);
    return {tool, identity:id, exit_code:r.code, output:r.stdout, error:r.stderr};
  }
  if (tool === 'read_tracked_file') {
    const rel = safeRelative(args.path);
    await ensureTracked(rel);
    const full = path.resolve(REPO, rel);
    if (!full.startsWith(REPO + path.sep)) throw new Error('path_escape_denied');
    const stat = await fs.stat(full);
    if (stat.size > MAX_FILE) throw new Error('file_too_large');
    const content = await fs.readFile(full, 'utf8');
    return {tool, identity:id, path:rel, content};
  }
  if (tool === 'search_tracked_text') {
    const pattern = String(args.pattern || '').trim();
    if (!pattern || pattern.length > 200) throw new Error('invalid_search_pattern');
    const r = await run(GIT, ['grep','-n','-I','-e',pattern,'--'], 20000);
    if (![0,1].includes(r.code)) throw new Error('git_grep_failed');
    return {tool, identity:id, exit_code:r.code, output:r.stdout.split(/\r?\n/).slice(0,300).join('\n')};
  }
  if (tool === 'run_n8n_fabric_tests') {
    const r = await run(UV, ['run','pytest','tests/test_n8n_development_agent_fabric.py','-q'], 180000);
    return {tool, identity:id, exit_code:r.code, output:r.stdout, error:r.stderr};
  }
  if (tool === 'run_n8n_fabric_ruff') {
    const r = await run(UV, ['run','ruff','check','integrations/n8n','tests/test_n8n_development_agent_fabric.py'], 120000);
    return {tool, identity:id, exit_code:r.code, output:r.stdout, error:r.stderr};
  }
  if (tool === 'run_test_file') {
    const rel = safeRelative(args.path);
    if (!/^tests\/test_[A-Za-z0-9_./-]+\.py$/.test(rel)) throw new Error('test_path_denied');
    await ensureTracked(rel);
    const r = await run(UV, ['run','pytest',rel,'-q'], 180000);
    return {tool, identity:id, path:rel, exit_code:r.code, output:r.stdout, error:r.stderr};
  }
  throw new Error('tool_not_allowed');
}

const server = http.createServer((req, res) => {
  if (req.method === 'GET' && req.url === '/health') {
    return respond(res, 200, {ok:true, service:'ck-nexus-dev-tool-gateway', mode:'development_only', repo:REPO});
  }
  if (req.method !== 'POST' || req.url !== '/v1/tool') return respond(res, 404, {error:'not_found'});
  let raw='';
  req.on('data', chunk => { raw += chunk; if (raw.length > 65536) req.destroy(); });
  req.on('end', async () => {
    try {
      const result = await executeTool(JSON.parse(raw || '{}'));
      respond(res, 200, {...result, production_mutation:false, raw_secret_access:false});
    } catch (error) {
      respond(res, 400, {error:String(error.message || error), mode:'fail_closed', production_mutation:false});
    }
  });
});

server.listen(PORT, HOST, () => console.log(`CK-NEXUS dev tool gateway listening on http://${HOST}:${PORT}`));
