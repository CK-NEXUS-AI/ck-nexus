import assert from 'node:assert/strict';
import test from 'node:test';
import { validateLoopbackPort } from './url-validation.js';

test('uses the fixed default local OpenCode port', () => {
  assert.equal(validateLoopbackPort(undefined), 18924);
  assert.equal(validateLoopbackPort(''), 18924);
});

test('accepts a valid explicit local TCP port', () => {
  assert.equal(validateLoopbackPort('19001'), 19001);
});

test('rejects URLs, non-numeric values, and out-of-range ports', () => {
  for (const value of ['https://remote.example', 'localhost:18924', '0', '65536', '-1', '1.5']) {
    assert.throws(() => validateLoopbackPort(value));
  }
});
