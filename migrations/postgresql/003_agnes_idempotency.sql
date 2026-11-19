CREATE TABLE IF NOT EXISTS agnes_idempotency (
    idem_key TEXT PRIMARY KEY,
    manifest_hash TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('running', 'succeeded', 'failed')),
    result_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agnes_idempotency_state_updated
    ON agnes_idempotency(state, updated_at DESC);
