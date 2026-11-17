import assert from 'node:assert/strict';
import test from 'node:test';
import { validateLoopbackBaseUrl } from './url-validation.js';

test('accepts IPv4 loopback upstream URLs', () => {
  assert.equal(validateLoopbackBaseUrl('http://127.0.0.1:18924/'), 'http://127.0.0.1:18924');
});

test('accepts IPv6 loopback upstream URLs', () => {
  assert.equal(validateLoopbackBaseUrl('http://[::1]:18924/'), 'http://[::1]:18924');
});

test('rejects remote hosts, DNS names, and credential-bearing URLs', () => {
  for (const value of [
    'https://opencode.example:18924/',
    'http://localhost:18924/',
    'http://127.0.0.1@evil.example:18924/',
    'http://user:pass@127.0.0.1:18924/',
    'http://127.0.0.1:18924/proxy',
    'http://127.0.0.1:18924/?next=https://evil.example',
  ]) {
    assert.throws(() => validateLoopbackBaseUrl(value));
  }
});
