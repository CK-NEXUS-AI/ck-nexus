import { createServer } from 'node:http';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { createMcpHandler, McpServer } from '@modelcontextprotocol/server';
import {
  localhostHostValidation,
  localhostOriginValidation,
  toNodeHandler,
} from '@modelcontextprotocol/node';
import * as z from 'zod/v4';

const execFileAsync = promisify(execFile);

const HOST = process.env.CKNEXUS_ANYCLAW_HOST ?? '127.0.0.1';
const PORT = Number(process.env.CKNEXUS_ANYCLAW_PORT ?? '18926');
const BRIDGE_TOKEN = process.env.CKNEXUS_ANYCLAW_TOKEN ?? '';
const ANYCLAW_BIN = process.env.ANYCLAW_BIN ?? 'anyclaw';
const MAX_OUTPUT = Number(process.env.CKNEXUS_ANYCLAW_MAX_OUTPUT ?? '65536');

function redact(value: string): string {
  return value
    .replace(/(?:sk|ghp|github_pat|xox[baprs]|AIza)[A-Za-z0-9_\-.]{10,}/g, '[REDACTED]')
    .replace(/Bearer\s+[A-Za-z0-9._~+\/-]+=*/gi, 'Bearer [REDACTED]')
    .replace(/Basic\s+[A-Za-z0-9+/=]+/gi, 'Basic [REDACTED]');
}

async function runAnyClaw(args: string[], timeoutMs = 60_000) {
  const { stdout, stderr } = await execFileAsync(ANYCLAW_BIN, args, {
    timeout: timeoutMs,
    maxBuffer: MAX_OUTPUT,
    env: process.env,
  });
  return {
    command: [ANYCLAW_BIN, ...args],
    stdout: redact(stdout.trim()),
    stderr: redact(stderr.trim()),
  };
}

function result(payload: unknown) {
  const safe = JSON.parse(redact(JSON.stringify(payload))) as Record<string, unknown>;
  return {
    content: [{ type: 'text' as const, text: JSON.stringify(safe, null, 2) }],
    structuredContent: safe,
  };
}

function buildServer(): McpServer {
  const server = new McpServer(
    { name: 'ck-nexus-anyclaw-control', version: '0.1.0' },
    {
      instructions:
        'AnyClaw is a read-only discovery adapter under CK-NEXUS. Execution and package mutation are disabled until CK-NEXUS Core approval, policy and evidence integration exists. Never request, print, persist, or expose raw credentials. Never use AnyClaw evidence to substitute for Q10 Native Codex Security evidence or to claim Production Ready.',
    },
  );

  server.registerTool(
    'anyclaw_version',
    {
      description: 'Use this when checking whether AnyClaw is installed and reachable on the bridge host.',
      annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false, idempotentHint: true },
    },
    async () => result(await runAnyClaw(['version'])),
  );

  server.registerTool(
    'anyclaw_list_installed',
    {
      description: 'Use this when listing installed AnyClaw packages and their available commands.',
      annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false, idempotentHint: true },
    },
    async () => result(await runAnyClaw(['list'])),
  );

  server.registerTool(
    'anyclaw_search_registry',
    {
      description: 'Use this when searching the AnyClaw package registry by keyword before deciding whether a package is needed.',
      inputSchema: z.object({ keyword: z.string().min(1).max(200) }),
      annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: true, idempotentHint: true },
    },
    // nosemgrep: typescript.mcp.security.mcp-ssrf-typescript -- this helper invokes a fixed local executable through execFile; no HTTP URL is constructed.
    async ({ keyword }) => result(await runAnyClaw(['search', keyword])),
  );

  server.registerTool(
    'anyclaw_daemon_status',
    {
      description: 'Use this when checking AnyClaw browser daemon and extension status.',
      annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false, idempotentHint: true },
    },
    async () => result(await runAnyClaw(['daemon', 'status'])),
  );

  // Execution, install and uninstall are intentionally not exposed here.
  // They must be routed through CK-NEXUS Core approval, policy and evidence
  // controls before this bridge can mutate a workspace or install capability.

  return server;
}

if (HOST !== '127.0.0.1' && HOST !== 'localhost' && !BRIDGE_TOKEN) {
  throw new Error('Refusing non-loopback bind without CKNEXUS_ANYCLAW_TOKEN');
}

const mcpHandler = createMcpHandler(buildServer);
const nodeHandler = toNodeHandler(mcpHandler);
const validateHost = localhostHostValidation();
const validateOrigin = localhostOriginValidation();

const httpServer = createServer((req, res) => {
  if (req.url === '/health') {
    res.writeHead(200, { 'content-type': 'application/json' });
    res.end(JSON.stringify({ healthy: true, service: 'ck-nexus-anyclaw-control', production_status: 'NO-GO' }));
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
  console.error(`[anyclaw-bridge] listening on http://${HOST}:${PORT}/mcp`);
  console.error(`[anyclaw-bridge] binary ${ANYCLAW_BIN}`);
});

async function shutdown() {
  await mcpHandler.close();
  httpServer.close(() => process.exit(0));
}

process.on('SIGINT', () => void shutdown());
process.on('SIGTERM', () => void shutdown());
