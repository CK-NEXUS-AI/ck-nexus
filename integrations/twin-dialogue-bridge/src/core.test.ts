import assert from 'node:assert/strict';
import test from 'node:test';
import { createRecord, normalizeBody, verifyRecord } from './core.js';

test('creates development-only advisory records with valid digest', () => {
  const record = createRecord({
    recordType: 'message',
    conversationId: 'cknexus-dual-dev',
    peerLabel: 'peer-a',
    intent: 'proposal',
    body: 'เสนอเพิ่ม governed peer dialogue bridge',
  });
  assert.equal(record.classification, 'DEVELOPMENT_ONLY');
  assert.equal(record.authority, 'ADVISORY_ONLY');
  assert.equal(record.production_evidence, false);
  assert.equal(verifyRecord(record), true);
});

test('rejects secret-like provider keys', () => {
  assert.throws(() => normalizeBody('key sk-abcdefghijklmnopqrstuvwxyz123456'), /SECRET_LIKE_CONTENT_REJECTED/);
});

test('rejects Telegram bot token-like content', () => {
  assert.throws(() => normalizeBody('123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi'), /SECRET_LIKE_CONTENT_REJECTED/);
});

test('detects tampered record', () => {
  const record = createRecord({
    recordType: 'message',
    conversationId: 'cknexus-dual-dev',
    peerLabel: 'peer-b',
    intent: 'critique',
    body: 'ตรวจ governance ก่อน merge',
  });
  const tampered = { ...record, body: 'changed' };
  assert.equal(verifyRecord(tampered), false);
});
