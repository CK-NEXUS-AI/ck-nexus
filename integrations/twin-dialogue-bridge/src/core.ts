import { createHash, randomUUID } from 'node:crypto';
import { appendFile, mkdir, readFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';

export const DEVELOPMENT_CLASSIFICATION = 'DEVELOPMENT_ONLY' as const;
export const ADVISORY_AUTHORITY = 'ADVISORY_ONLY' as const;

export type DialogueIntent =
  | 'proposal'
  | 'critique'
  | 'evidence_request'
  | 'evidence_response'
  | 'implementation_handoff'
  | 'decision_recommendation'
  | 'status';

export type DialogueRecord = {
  schema_version: 1;
  record_id: string;
  record_type: 'message' | 'context' | 'ack';
  conversation_id: string;
  peer_label: string;
  intent: DialogueIntent | 'context' | 'ack';
  body: string;
  created_at: string;
  correlation_id: string;
  causation_id?: string;
  source_url?: string;
  source_digest?: string;
  evidence_refs: string[];
  classification: typeof DEVELOPMENT_CLASSIFICATION;
  authority: typeof ADVISORY_AUTHORITY;
  production_evidence: false;
  digest_sha256: string;
};

const SECRET_PATTERNS: Array<{ name: string; pattern: RegExp }> = [
  { name: 'provider_api_key', pattern: /\b(?:sk-|gsk_|ghp_|github_pat_|xox[baprs]-?)[A-Za-z0-9_.-]{10,}\b/i },
  { name: 'google_api_key', pattern: /\bAIza[0-9A-Za-z_-]{20,}\b/ },
  { name: 'telegram_bot_token', pattern: /\b\d{6,12}:[A-Za-z0-9_-]{20,}\b/ },
  { name: 'aws_access_key', pattern: /\b(?:AKIA|ASIA)[A-Z0-9]{16}\b/ },
  { name: 'jwt', pattern: /\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b/ },
  { name: 'bearer_token', pattern: /\bBearer\s+[A-Za-z0-9._~+\/-]{16,}={0,2}\b/i },
  { name: 'private_key', pattern: /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/ },
];

export function assertNoSecretLikeContent(value: string): void {
  for (const { name, pattern } of SECRET_PATTERNS) {
    if (pattern.test(value)) {
      throw new Error(`SECRET_LIKE_CONTENT_REJECTED:${name}`);
    }
  }
}

export function assertSafeIdentifier(value: string, field: string): string {
  const trimmed = value.trim();
  if (!/^[A-Za-z0-9._:-]{1,128}$/.test(trimmed)) {
    throw new Error(`${field.toUpperCase()}_INVALID`);
  }
  return trimmed;
}

export function normalizeBody(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) throw new Error('BODY_REQUIRED');
  if (trimmed.length > 20_000) throw new Error('BODY_TOO_LARGE');
  assertNoSecretLikeContent(trimmed);
  return trimmed;
}

function stable(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(stable);
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([key, item]) => [key, stable(item)]),
    );
  }
  return value;
}

export function sha256(value: unknown): string {
  const serialized = typeof value === 'string' ? value : JSON.stringify(stable(value));
  return createHash('sha256').update(serialized).digest('hex');
}

export function createRecord(input: {
  recordType: DialogueRecord['record_type'];
  conversationId: string;
  peerLabel: string;
  intent: DialogueRecord['intent'];
  body: string;
  correlationId?: string;
  causationId?: string;
  sourceUrl?: string;
  evidenceRefs?: string[];
}): DialogueRecord {
  const conversationId = assertSafeIdentifier(input.conversationId, 'conversation_id');
  const peerLabel = assertSafeIdentifier(input.peerLabel, 'peer_label');
  const body = normalizeBody(input.body);
  const correlationId = input.correlationId
    ? assertSafeIdentifier(input.correlationId, 'correlation_id')
    : `corr_${randomUUID()}`;
  const causationId = input.causationId
    ? assertSafeIdentifier(input.causationId, 'causation_id')
    : undefined;
  const evidenceRefs = [...new Set(input.evidenceRefs ?? [])].slice(0, 20);
  for (const ref of evidenceRefs) {
    if (ref.length > 512) throw new Error('EVIDENCE_REF_TOO_LARGE');
    assertNoSecretLikeContent(ref);
  }
  if (input.sourceUrl) {
    if (input.sourceUrl.length > 2048) throw new Error('SOURCE_URL_TOO_LARGE');
    assertNoSecretLikeContent(input.sourceUrl);
  }

  const unsigned = {
    schema_version: 1 as const,
    record_id: `dlg_${randomUUID()}`,
    record_type: input.recordType,
    conversation_id: conversationId,
    peer_label: peerLabel,
    intent: input.intent,
    body,
    created_at: new Date().toISOString(),
    correlation_id: correlationId,
    ...(causationId ? { causation_id: causationId } : {}),
    ...(input.sourceUrl ? { source_url: input.sourceUrl, source_digest: sha256(input.sourceUrl) } : {}),
    evidence_refs: evidenceRefs,
    classification: DEVELOPMENT_CLASSIFICATION,
    authority: ADVISORY_AUTHORITY,
    production_evidence: false as const,
  };

  return { ...unsigned, digest_sha256: sha256(unsigned) };
}

export async function appendRecord(path: string, record: DialogueRecord): Promise<void> {
  const absolute = resolve(path);
  await mkdir(dirname(absolute), { recursive: true });
  await appendFile(absolute, `${JSON.stringify(record)}\n`, { encoding: 'utf-8', mode: 0o600 });
}

export async function readRecords(path: string): Promise<DialogueRecord[]> {
  try {
    const text = await readFile(resolve(path), 'utf-8');
    return text
      .split('\n')
      .filter(Boolean)
      .map((line) => JSON.parse(line) as DialogueRecord);
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') return [];
    throw error;
  }
}

export function verifyRecord(record: DialogueRecord): boolean {
  const { digest_sha256, ...unsigned } = record;
  return digest_sha256 === sha256(unsigned);
}
