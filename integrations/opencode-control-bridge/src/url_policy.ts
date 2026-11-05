import { isIP } from 'node:net';
import * as z from 'zod/v4';

export const SESSION_ID_SCHEMA = z.string().regex(/^[A-Za-z0-9_-]{1,128}$/);

export function normalizeOpenCodeBaseUrl(value: string): string {
  let parsed: URL;
  try {
    parsed = new URL(value);
  } catch {
    throw new Error('OPENCODE_BASE_URL must be a valid URL');
  }

  const hostname = parsed.hostname.toLowerCase();
  const ip = hostname.startsWith('[') && hostname.endsWith(']')
    ? hostname.slice(1, -1)
    : hostname;
  const numericLoopback = ip === '127.0.0.1' || ip === '::1';
  if (!['http:', 'https:'].includes(parsed.protocol) || !numericLoopback || isIP(ip) === 0) {
    throw new Error('OPENCODE_BASE_URL must target a numeric loopback IP address');
  }
  if (parsed.username || parsed.password || parsed.search || parsed.hash) {
    throw new Error('OPENCODE_BASE_URL must not contain credentials, query, or fragment');
  }
  if (parsed.pathname !== '/' && parsed.pathname !== '') {
    throw new Error('OPENCODE_BASE_URL must not contain a path prefix');
  }
  return parsed.origin;
}

export function buildOpenCodeRequestUrl(baseUrl: string, path: string): string {
  const base = new URL(normalizeOpenCodeBaseUrl(baseUrl));
  const target = new URL(path, base);
  if (target.origin !== base.origin) {
    throw new Error('OpenCode request path must remain on the configured loopback origin');
  }
  return z.parse(z.string().url(), target.toString());
}
