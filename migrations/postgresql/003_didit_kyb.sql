CREATE TABLE IF NOT EXISTS didit_webhook_events (
    event_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    vendor_data TEXT NOT NULL,
    status TEXT NOT NULL,
    received_at BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS didit_business_verifications (
    vendor_data TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    status TEXT NOT NULL,
    verified BOOLEAN NOT NULL DEFAULT FALSE,
    decision_json JSONB,
    resubmit_json JSONB,
    updated_at BIGINT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_didit_webhook_session
    ON didit_webhook_events (session_id);

CREATE INDEX IF NOT EXISTS idx_didit_business_status
    ON didit_business_verifications (status);
