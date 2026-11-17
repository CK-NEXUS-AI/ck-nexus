/** Validate the local OpenCode port; the upstream host is a fixed loopback literal. */
export function validateLoopbackPort(value: string | undefined): number {
  if (value === undefined || value.trim() === '') return 18924;
  if (!/^\d{1,5}$/.test(value)) {
    throw new Error('OPENCODE_PORT must be a decimal TCP port');
  }
  const port = Number(value);
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new Error('OPENCODE_PORT must be between 1 and 65535');
  }
  return port;
}
