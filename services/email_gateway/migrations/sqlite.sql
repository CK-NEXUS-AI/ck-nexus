PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS email_journal (
    id TEXT PRIMARY KEY,
    mailbox TEXT NOT NULL,
    provider TEXT NOT NULL,
    provider_message_id TEXT NOT NULL,
    internet_message_id TEXT,
    idempotency_key TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'PROCESSING'
        CHECK (status IN ('PROCESSING','COMPLETED','FAILED_RETRYABLE','FAILED_PERMANENT')),
    claimed_by TEXT,
    locked_until TEXT,
    attempt_count INTEGER NOT NULL DEFAULT 1 CHECK (attempt_count >= 1),
    first_seen_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT,
    last_error_code TEXT,
    last_error_at TEXT,
    UNIQUE (mailbox, provider, provider_message_id)
);

CREATE INDEX IF NOT EXISTS idx_email_journal_status_lease
    ON email_journal(status, locked_until);

CREATE TABLE IF NOT EXISTS email_outbox (
    id TEXT PRIMARY KEY,
    email_journal_id TEXT NOT NULL REFERENCES email_journal(id) ON DELETE CASCADE,
    action_type TEXT NOT NULL,
    destination TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    deduplication_key TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING','SENDING','SENT','FAILED_RETRYABLE','FAILED_PERMANENT')),
    provider_message_id TEXT,
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    next_attempt_at TEXT NOT NULL,
    locked_until TEXT,
    claimed_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    sent_at TEXT,
    last_error TEXT
);

CREATE INDEX IF NOT EXISTS idx_email_outbox_ready
    ON email_outbox(status, next_attempt_at, locked_until);


CREATE TABLE IF NOT EXISTS email_audit_logs (
    id TEXT PRIMARY KEY,
    email_journal_id TEXT REFERENCES email_journal(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    actor_type TEXT NOT NULL,
    actor_id TEXT,
    routing_category TEXT,
    action TEXT,
    result TEXT NOT NULL,
    details_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_email_audit_journal_created
    ON email_audit_logs(email_journal_id, created_at);
