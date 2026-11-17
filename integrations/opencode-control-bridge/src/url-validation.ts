/** Validate the local OpenCode upstream before Basic credentials are attached. */
export function validateLoopbackBaseUrl(value: string): string {
  let parsed: URL;
  try {
    parsed = new URL(value);
  } catch {
    throw new Error('OPENCODE_BASE_URL must be a valid URL');
  }

  const hostname = parsed.hostname.replace(/^\[|\]$/g, '').toLowerCase();
  if (!['127.0.0.1', '::1'].includes(hostname)) {
    throw new Error('OPENCODE_BASE_URL must use a loopback IP literal');
  }
  if (!['http:', 'https:'].includes(parsed.protocol)) {
    throw new Error('OPENCODE_BASE_URL must use HTTP or HTTPS');
  }
  if (parsed.username || parsed.password || parsed.search || parsed.hash || parsed.pathname !== '/') {
    throw new Error('OPENCODE_BASE_URL must not contain credentials, a path, query, or fragment');
  }
  return parsed.origin;
}
