import { createServer } from 'node:http';
import { createMcpHandler, McpServer } from '@modelcontextprotocol/server';
import {
  localhostHostValidation,
  localhostOriginValidation,
  toNodeHandler,
} from '@modelcontextprotocol/node';
import * as z from 'zod/v4';
import { buildOpenCodeRequestUrl, normalizeOpenCodeBaseUrl, SESSION_ID_SCHEMA } from './url_policy.js';

const HOST = process.env.CKNEXUS_BRIDGE_HOST ?? '127.0.0.1';
const PORT = Number(process.env.CKNEXUS_BRIDGE_PORT ?? '18925');
const OPENCODE_BASE_URL = normalizeOpenCodeBaseUrl(
  process.env.OPENCODE_BASE_URL ?? 'http://127.0.0.1:18924',
);
const OPENCODE_USERNAME = process.env.OPENCODE_SERVER_USERNAME ?? 'opencode';
const OPENCODE_PASSWORD = process.env.OPENCODE_SERVER_PASSWORD ?? '';
const BRIDGE_TOKEN = process.env.CKNEXUS_BRIDGE_TOKEN ?? '';

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
  const url = buildOpenCodeRequestUrl(OPENCODE_BASE_URL, path);
  const safeUrl = z.parse(z.string().url(), url);
  // nosemgrep: home.runner.work._temp.semgrep-rules.typescript.mcp.security.mcp-ssrf-typescript -- The URL is built from a numeric-loopback base, origin-checked, Zod-parsed, and covered by URL policy regression tests; the interprocedural MCP taint rule does not follow this validation helper.
  const response = await fetch(safeUrl, {
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
  const safeSessionId = SESSION_ID_SCHEMA.parse(sessionId);
  return ocRequest(`/session/${encodeURIComponent(safeSessionId)}/message?limit=${limit}`);
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
        'This bridge is read-only. Workspace mutation is disabled until CK-NEXUS Core approval, policy and evidence integration exists. Keep production fail-closed and never expose secrets or bypass provider restrictions.',
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
      description: 'Use this when discovering OpenCode sessions before selecting one for read-only inspection.',
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
        sessionId: SESSION_ID_SCHEMA,
        limit: z.number().int().min(1).max(50).default(20),
      }),
      annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false, idempotentHint: true },
    },
    async ({ sessionId, limit }) => {
      const safeSessionId = SESSION_ID_SCHEMA.parse(sessionId);
      return result(await getMessages(safeSessionId, limit));
    },
  );

  // Workspace mutation, continuation and abort are not exposed by this bridge.
  // They require CK-NEXUS Core approval, policy and evidence integration first.

  return server;
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
});

async function shutdown() {
  await mcpHandler.close();
  httpServer.close(() => process.exit(0));
}

process.on('SIGINT', () => void shutdown());
process.on('SIGTERM', () => void shutdown());
