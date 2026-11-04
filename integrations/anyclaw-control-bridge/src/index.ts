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
        'AnyClaw is a governed execution adapter under CK-NEXUS. Use read-only discovery first. Never request, print, persist, or expose raw credentials. Never use AnyClaw evidence to substitute for Q10 Native Codex Security evidence or to claim Production Ready.',
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

  server.registerTool(
    'anyclaw_run',
    {
      description: 'Use this when invoking one explicitly selected installed AnyClaw package command. Arguments are passed directly to AnyClaw; never include raw API keys, passwords, tokens, or credentials.',
      inputSchema: z.object({
        packageName: z.string().regex(/^[A-Za-z0-9_.-]+$/),
        command: z.string().regex(/^[A-Za-z0-9_.-]+$/),
        args: z.array(z.string().max(2000)).max(64).default([]),
      }),
      annotations: { readOnlyHint: false, destructiveHint: false, openWorldHint: true, idempotentHint: false },
    },
    // nosemgrep: typescript.mcp.security.mcp-ssrf-typescript -- arguments are passed to execFile for the local AnyClaw CLI, not to fetch or an HTTP client.
    async ({ packageName, command, args }) => {
      // nosemgrep: typescript.mcp.security.mcp-ssrf-typescript -- args are validated strings passed as argv to a fixed local execFile target, never as a URL.
      for (const arg of args) {
        if (/(?:sk-|ghp_|github_pat_|xox[baprs]-|AIza|bearer\s+|authorization:|api[_-]?key|password|token)/i.test(arg)) {
          throw new Error('Refusing argument that appears to contain credential material');
        }
      }
      // nosemgrep: typescript.mcp.security.mcp-ssrf-typescript -- runAnyClaw uses execFile with shell disabled and a fixed executable.
      return result(await runAnyClaw(['run', packageName, command, ...args], 120_000));
    },
  );

  server.registerTool(
    'anyclaw_install',
    {
      description: 'Use this only when installing a specifically selected AnyClaw package from the official registry or an explicitly trusted URL/path. Installation changes local tool capability and is not production evidence.',
      inputSchema: z.object({ source: z.string().min(1).max(2000) }),
      annotations: { readOnlyHint: false, destructiveHint: false, openWorldHint: true, idempotentHint: false },
    },
    // nosemgrep: typescript.mcp.security.mcp-ssrf-typescript -- source is passed to execFile for the local AnyClaw CLI; it is not used as a request URL.
    async ({ source }) => {
      // nosemgrep: typescript.mcp.security.mcp-ssrf-typescript -- source is a CLI argument to a fixed local executable, not an HTTP request URL.
      if (/(?:token|password|api[_-]?key|authorization)/i.test(source)) {
        throw new Error('Refusing install source that appears to contain credential material');
      }
      // nosemgrep: typescript.mcp.security.mcp-ssrf-typescript -- source is passed to execFile argv for the local AnyClaw CLI, never to fetch.
      return result(await runAnyClaw(['install', source], 180_000));
    },
  );

  server.registerTool(
    'anyclaw_uninstall',
    {
      description: 'Use this only when explicitly removing an installed AnyClaw package is necessary.',
      inputSchema: z.object({ packageName: z.string().regex(/^[A-Za-z0-9_.-]+$/) }),
      annotations: { readOnlyHint: false, destructiveHint: true, openWorldHint: false, idempotentHint: true },
    },
    // nosemgrep: typescript.mcp.security.mcp-ssrf-typescript -- packageName is regex-constrained and passed to a fixed local execFile target.
    async ({ packageName }) => result(await runAnyClaw(['uninstall', packageName], 120_000)),
  );

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
