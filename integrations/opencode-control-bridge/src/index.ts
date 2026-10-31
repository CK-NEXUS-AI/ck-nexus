import { createServer } from 'node:http';
import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { createMcpHandler, McpServer } from '@modelcontextprotocol/server';
import {
  localhostHostValidation,
  localhostOriginValidation,
  toNodeHandler,
} from '@modelcontextprotocol/node';
import * as z from 'zod/v4';

const HOST = process.env.CKNEXUS_BRIDGE_HOST ?? '127.0.0.1';
const PORT = Number(process.env.CKNEXUS_BRIDGE_PORT ?? '18925');
const OPENCODE_BASE_URL = (process.env.OPENCODE_BASE_URL ?? 'http://127.0.0.1:18924').replace(/\/$/, '');
const OPENCODE_USERNAME = process.env.OPENCODE_SERVER_USERNAME ?? 'opencode';
const OPENCODE_PASSWORD = process.env.OPENCODE_SERVER_PASSWORD ?? '';
const BRIDGE_TOKEN = process.env.CKNEXUS_BRIDGE_TOKEN ?? '';
const DEFAULT_SESSION_ID = process.env.OPENCODE_SESSION_ID ?? '';
const AUTOSTART = (process.env.CKNEXUS_AUTOSTART ?? 'false').toLowerCase() === 'true';
const STATE_FILE = process.env.CKNEXUS_BRIDGE_STATE_FILE ?? '.opencode-bridge-state.json';

const EXPECTED_SOURCE_SHA = 'fe81c22da08913fd9fd9b37d4c80e459668e1362';
const EXPECTED_TREE = '0525195934f703a8becf8a39f6397b2411e0bb2e';
const EXPECTED_RUNTIME_SUBJECT = '211a12d7b5759de7babdd882d2e527d5b6d1c1fe5ccec19084784232a44435f1';

const CONTINUE_PROMPT = `Continue the pending CK-NEXUS work automatically from the latest exact repository evidence.

Authority rules:
- Latest exact GitHub evidence wins.
- Production remains NO-GO until Q10 -> Q11 -> Q12 -> provenance -> Final Production Package all pass with genuine evidence.
- Never fabricate evidence or credentials.
- Never expose secrets.
- Never weaken gates.
- Never merge PR #14.
- Do not modify frozen runtime subject without a justified closure-contract reason.
- Fail closed on uncertainty or subject mismatch.

Frozen scan target:
SOURCE SHA: ${EXPECTED_SOURCE_SHA}
TREE: ${EXPECTED_TREE}
RUNTIME SUBJECT: ${EXPECTED_RUNTIME_SUBJECT}

Work autonomously on safe development/preparation tasks, verify all changes, update GitHub evidence/handoff, and stop only on a real external prerequisite or policy blocker. Do not claim Native Codex Security Q10 PASS unless genuine Native Codex Security sealed evidence exists.`;

function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = { 'content-type': 'application/json' };
  if (OPENCODE_PASSWORD) {
    headers.authorization = `Basic ${Buffer.from(`${OPENCODE_USERNAME}:${OPENCODE_PASSWORD}`).toString('base64')}`;
  }
  return headers;
}

function redact(value: unknown): unknown {
  if (typeof value === 'string') {
    return value
      .replace(/(?:sk|ghp|github_pat|xox[baprs]|AIza)[A-Za-z0-9_\-.]{10,}/g, '[REDACTED]')
      .replace(/Bearer\s+[A-Za-z0-9._~+\/-]+=*/gi, 'Bearer [REDACTED]')
      .replace(/Basic\s+[A-Za-z0-9+/=]+/gi, 'Basic [REDACTED]');
  }
  if (Array.isArray(value)) return value.map(redact);
  if (value && typeof value === 'object') {
    const out: Record<string, unknown> = {};
    for (const [key, item] of Object.entries(value as Record<string, unknown>)) {
      if (/token|secret|password|api[_-]?key|authorization|credential/i.test(key)) {
        out[key] = '[REDACTED]';
      } else {
        out[key] = redact(item);
      }
    }
    return out;
  }
  return value;
}

async function ocRequest(path: string, init: RequestInit = {}): Promise<unknown> {
  const url = `${OPENCODE_BASE_URL}${path}`;
  const response = await fetch(url, {
    ...init,
    headers: { ...authHeaders(), ...(init.headers ?? {}) },
    signal: AbortSignal.timeout(30_000),
  });
  if (!response.ok) {
    throw new Error(`OpenCode HTTP ${response.status} on ${path}`);
  }
  if (response.status === 204) return { accepted: true };
  const text = await response.text();
  if (!text) return {};
  return JSON.parse(text);
}

async function health(): Promise<unknown> {
  return ocRequest('/global/health');
}

async function listSessions(): Promise<unknown> {
  return ocRequest('/session');
}

async function sessionStatus(): Promise<unknown> {
  return ocRequest('/session/status');
}

async function getMessages(sessionId: string, limit: number): Promise<unknown> {
  return ocRequest(`/session/${encodeURIComponent(sessionId)}/message?limit=${limit}`);
}

async function sendPromptAsync(sessionId: string, prompt: string): Promise<unknown> {
  return ocRequest(`/session/${encodeURIComponent(sessionId)}/prompt_async`, {
    method: 'POST',
    body: JSON.stringify({ parts: [{ type: 'text', text: prompt }] }),
  });
}

async function abortSession(sessionId: string): Promise<unknown> {
  return ocRequest(`/session/${encodeURIComponent(sessionId)}/abort`, {
    method: 'POST',
    body: JSON.stringify({}),
  });
}

function result(payload: unknown) {
  const safe = redact(payload);
  return {
    content: [{ type: 'text' as const, text: JSON.stringify(safe, null, 2) }],
    structuredContent: safe as Record<string, unknown>,
  };
}

function buildServer(): McpServer {
  const server = new McpServer(
    { name: 'ck-nexus-opencode-control', version: '0.1.0' },
    {
      instructions:
        'Use read-only status tools before mutation. Keep CK-NEXUS production fail-closed. Never expose secrets or use this bridge to bypass provider restrictions. opencode_continue_cknexus is the preferred governed continuation action.',
    },
  );

  server.registerTool(
    'opencode_health',
    {
      description: 'Use this when checking whether the local OpenCode HTTP server is reachable and healthy.',
      annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false, idempotentHint: true },
    },
    async () => result(await health()),
  );

  server.registerTool(
    'opencode_list_sessions',
    {
      description: 'Use this when discovering OpenCode sessions before selecting one to inspect or continue.',
      annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false, idempotentHint: true },
    },
    async () => result(await listSessions()),
  );

  server.registerTool(
    'opencode_session_status',
    {
      description: 'Use this when checking current status of OpenCode sessions, including whether work is active or idle.',
      annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false, idempotentHint: true },
    },
    async () => result(await sessionStatus()),
  );

  server.registerTool(
    'opencode_get_messages',
    {
      description: 'Use this when reading recent redacted messages from one OpenCode session.',
      inputSchema: z.object({
        sessionId: z.string().min(1),
        limit: z.number().int().min(1).max(50).default(20),
      }),
      annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false, idempotentHint: true },
    },
    async ({ sessionId, limit }) => result(await getMessages(sessionId, limit)),
  );

  server.registerTool(
    'opencode_run_prompt',
    {
      description: 'Use this when sending an explicitly provided task to an authorized OpenCode session. The request is asynchronous and may modify the workspace according to OpenCode permissions.',
      inputSchema: z.object({
        sessionId: z.string().min(1),
        prompt: z.string().min(1).max(20_000),
      }),
      annotations: { readOnlyHint: false, destructiveHint: false, openWorldHint: true, idempotentHint: false },
    },
    async ({ sessionId, prompt }) => result(await sendPromptAsync(sessionId, prompt)),
  );

  server.registerTool(
    'opencode_continue_cknexus',
    {
      description: 'Use this when resuming the pending CK-NEXUS work under the fixed Evidence-First, Exact-Subject, Fail-Closed production policy. It never authorizes Production Ready or PR #14 merge.',
      inputSchema: z.object({
        sessionId: z.string().min(1).optional(),
      }),
      annotations: { readOnlyHint: false, destructiveHint: false, openWorldHint: true, idempotentHint: false },
    },
    async ({ sessionId }) => {
      const id = sessionId || DEFAULT_SESSION_ID;
      if (!id) throw new Error('sessionId is required or OPENCODE_SESSION_ID must be configured');
      await health();
      return result(await sendPromptAsync(id, CONTINUE_PROMPT));
    },
  );

  server.registerTool(
    'opencode_abort_session',
    {
      description: 'Use this only when stopping a currently running OpenCode session is explicitly necessary for safety or operator intent.',
      inputSchema: z.object({ sessionId: z.string().min(1) }),
      annotations: { readOnlyHint: false, destructiveHint: true, openWorldHint: false, idempotentHint: true },
    },
    async ({ sessionId }) => result(await abortSession(sessionId)),
  );

  return server;
}

async function loadState(): Promise<Record<string, unknown>> {
  try {
    return JSON.parse(await readFile(STATE_FILE, 'utf8')) as Record<string, unknown>;
  } catch {
    return {};
  }
}

async function saveState(state: Record<string, unknown>): Promise<void> {
  await writeFile(STATE_FILE, `${JSON.stringify(state, null, 2)}\n`, { mode: 0o600 });
}

async function maybeAutostart(): Promise<void> {
  if (!AUTOSTART || !DEFAULT_SESSION_ID) return;
  const state = await loadState();
  const promptHash = createHash('sha256').update(CONTINUE_PROMPT).digest('hex');
  if (state.autostart_session === DEFAULT_SESSION_ID && state.autostart_prompt_sha256 === promptHash) return;
  try {
    await health();
    await sendPromptAsync(DEFAULT_SESSION_ID, CONTINUE_PROMPT);
    await saveState({
      autostart_session: DEFAULT_SESSION_ID,
      autostart_prompt_sha256: promptHash,
      sent_at: new Date().toISOString(),
      production_status: 'NO-GO',
    });
    console.error('[bridge] CK-NEXUS continuation accepted by OpenCode');
  } catch (error) {
    console.error(`[bridge] autostart blocked: ${(error as Error).message}`);
    setTimeout(() => void maybeAutostart(), 15_000).unref();
  }
}

if (HOST !== '127.0.0.1' && HOST !== 'localhost' && !BRIDGE_TOKEN) {
  throw new Error('Refusing non-loopback bind without CKNEXUS_BRIDGE_TOKEN');
}

const mcpHandler = createMcpHandler(buildServer);
const nodeHandler = toNodeHandler(mcpHandler);
const validateHost = localhostHostValidation();
const validateOrigin = localhostOriginValidation();

const httpServer = createServer((req, res) => {
  if (req.url === '/health') {
    res.writeHead(200, { 'content-type': 'application/json' });
    res.end(JSON.stringify({ healthy: true, service: 'ck-nexus-opencode-control', production_status: 'NO-GO' }));
    return;
  }

  if (req.url !== '/mcp') {
    res.writeHead(404).end();
    return;
  }

  if (BRIDGE_TOKEN) {
    const auth = req.headers.authorization ?? '';
    if (auth !== `Bearer ${BRIDGE_TOKEN}`) {
      res.writeHead(401, { 'www-authenticate': 'Bearer' }).end();
      return;
    }
  }

  if (HOST === '127.0.0.1' || HOST === 'localhost') {
    if (!validateHost(req, res) || !validateOrigin(req, res)) return;
  }

  void nodeHandler(req, res);
});

httpServer.listen(PORT, HOST, () => {
  console.error(`[bridge] listening on http://${HOST}:${PORT}/mcp`);
  console.error(`[bridge] OpenCode upstream ${OPENCODE_BASE_URL}`);
  void maybeAutostart();
});

async function shutdown() {
  await mcpHandler.close();
  httpServer.close(() => process.exit(0));
}

process.on('SIGINT', () => void shutdown());
process.on('SIGTERM', () => void shutdown());
