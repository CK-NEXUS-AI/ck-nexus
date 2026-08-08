BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS email_journal (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mailbox TEXT NOT NULL,
    provider TEXT NOT NULL,
    provider_message_id TEXT NOT NULL,
    internet_message_id TEXT,
    idempotency_key TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PROCESSING'
        CHECK (status IN ('PROCESSING','COMPLETED','FAILED_RETRYABLE','FAILED_PERMANENT')),
    claimed_by TEXT,
    locked_until TIMESTAMPTZ,
    attempt_count INTEGER NOT NULL DEFAULT 1 CHECK (attempt_count >= 1),
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    last_error_code TEXT,
    last_error_at TIMESTAMPTZ,
    CONSTRAINT uq_email_provider_message UNIQUE (mailbox, provider, provider_message_id),
    CONSTRAINT uq_email_idempotency_key UNIQUE (idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_email_journal_status_lease
    ON email_journal(status, locked_until);

CREATE TABLE IF NOT EXISTS email_outbox (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_journal_id UUID NOT NULL REFERENCES email_journal(id) ON DELETE CASCADE,
    action_type TEXT NOT NULL,
    destination TEXT NOT NULL,
    payload JSONB NOT NULL,
    deduplication_key TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING','SENDING','SENT','FAILED_RETRYABLE','FAILED_PERMANENT')),
    provider_message_id TEXT,
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    locked_until TIMESTAMPTZ,
    claimed_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sent_at TIMESTAMPTZ,
    last_error TEXT
);

CREATE INDEX IF NOT EXISTS idx_email_outbox_ready
    ON email_outbox(status, next_attempt_at, locked_until);

CREATE TABLE IF NOT EXISTS email_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_journal_id UUID REFERENCES email_journal(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    actor_type TEXT NOT NULL,
    actor_id TEXT,
    routing_category TEXT,
    action TEXT,
    result TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_email_audit_journal_created
    ON email_audit_logs(email_journal_id, created_at);

COMMIT;
