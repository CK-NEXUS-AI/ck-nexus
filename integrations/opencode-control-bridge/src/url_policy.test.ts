import assert from 'node:assert/strict';
import test from 'node:test';

import { buildOpenCodeRequestUrl, normalizeOpenCodeBaseUrl, SESSION_ID_SCHEMA } from './url_policy.js';

test('accepts the configured IPv4 loopback endpoint', () => {
  assert.equal(
    normalizeOpenCodeBaseUrl('http://127.0.0.1:18924/'),
    'http://127.0.0.1:18924',
  );
});

test('accepts the IPv6 loopback endpoint', () => {
  assert.equal(normalizeOpenCodeBaseUrl('http://[::1]:18924'), 'http://[::1]:18924');
});

test('rejects DNS names and non-loopback destinations', () => {
  assert.throws(() => normalizeOpenCodeBaseUrl('http://localhost:18924'));
  assert.throws(() => normalizeOpenCodeBaseUrl('http://192.168.1.20:18924'));
  assert.throws(() => normalizeOpenCodeBaseUrl('http://169.254.169.254'));
});

test('rejects URL credentials, query and fragment', () => {
  assert.throws(() => normalizeOpenCodeBaseUrl('http://user:pass@127.0.0.1:18924'));
  assert.throws(() => normalizeOpenCodeBaseUrl('http://127.0.0.1:18924/?target=local'));
  assert.throws(() => normalizeOpenCodeBaseUrl('http://127.0.0.1:18924/#fragment'));
});


test('rejects path prefixes that could be discarded by root-relative API paths', () => {
  assert.throws(() => normalizeOpenCodeBaseUrl('http://127.0.0.1:18924/opencode'));
});

test('accepts opaque OpenCode session identifiers', () => {
  assert.equal(SESSION_ID_SCHEMA.parse('ses_0123456789abcdef'), 'ses_0123456789abcdef');
});

test('rejects path and URL injection in session identifiers', () => {
  for (const value of ['../admin', 'session/other', 'http://127.0.0.1', 'ses%2fadmin']) {
    assert.throws(() => SESSION_ID_SCHEMA.parse(value));
  }
});

test('builds request URLs only on the configured loopback origin', () => {
  assert.equal(
    buildOpenCodeRequestUrl('http://127.0.0.1:18924', '/session/ses_0123456789abcdef/message?limit=20'),
    'http://127.0.0.1:18924/session/ses_0123456789abcdef/message?limit=20',
  );
  assert.throws(() => buildOpenCodeRequestUrl('http://127.0.0.1:18924', '//example.com/path'));
  assert.throws(() => buildOpenCodeRequestUrl('http://127.0.0.1:18924', 'https://example.com/path'));
});
