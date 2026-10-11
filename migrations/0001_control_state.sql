-- CK-NEXUS Control State schema proposal.
-- DESIGN ONLY: do not apply to production. Review and test on disposable PostgreSQL first.
-- Secret payloads, OAuth tokens, API keys and email contents are intentionally excluded.

BEGIN;

CREATE TABLE IF NOT EXISTS evidence_registry (
    evidence_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evidence_type TEXT NOT NULL,
    source_system TEXT NOT NULL,
    source_record_id TEXT NOT NULL,
    source_revision TEXT,
    observed_at TIMESTAMPTZ NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    artifact_uri TEXT,
    sha256_hex CHAR(64),
    signature_ref TEXT,
    verifier_identity TEXT,
    verification_status TEXT NOT NULL CHECK (verification_status IN ('VERIFIED','EXECUTED','NOT_VERIFIED','BLOCKED')),
    limitations JSONB NOT NULL DEFAULT '[]'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    CHECK (sha256_hex IS NULL OR sha256_hex ~ '^[0-9a-f]{64}$')
);
CREATE INDEX IF NOT EXISTS idx_evidence_source_lookup
    ON evidence_registry (source_system, source_record_id, observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_evidence_status_time
    ON evidence_registry (verification_status, observed_at DESC);

CREATE TABLE IF NOT EXISTS workflow_registry (
    workflow_observation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id TEXT NOT NULL,
    workflow_name TEXT NOT NULL,
    source_instance TEXT NOT NULL,
    active BOOLEAN NOT NULL,
    workflow_version TEXT,
    observed_at TIMESTAMPTZ NOT NULL,
    last_execution_id TEXT,
    last_execution_status TEXT,
    evidence_id UUID REFERENCES evidence_registry(evidence_id),
    limitations JSONB NOT NULL DEFAULT '[]'::jsonb,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_workflow_registry_lookup
    ON workflow_registry (source_instance, workflow_id, observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_workflow_registry_evidence
    ON workflow_registry (evidence_id);

CREATE TABLE IF NOT EXISTS credential_registry (
    credential_observation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    credential_ref TEXT NOT NULL,
    credential_name TEXT NOT NULL,
    credential_type TEXT NOT NULL,
    owner_ref TEXT,
    scopes JSONB NOT NULL DEFAULT '[]'::jsonb,
    status TEXT NOT NULL CHECK (status IN ('VERIFIED','EXECUTED','NOT_VERIFIED','BLOCKED','DISABLED','REVOKED')),
    last_verified_at TIMESTAMPTZ,
    observed_at TIMESTAMPTZ NOT NULL,
    evidence_id UUID REFERENCES evidence_registry(evidence_id),
    limitations JSONB NOT NULL DEFAULT '[]'::jsonb,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (credential_ref, observed_at)
);
CREATE INDEX IF NOT EXISTS idx_credential_registry_evidence
    ON credential_registry (evidence_id);
CREATE INDEX IF NOT EXISTS idx_credential_registry_status_time
    ON credential_registry (status, observed_at DESC);

CREATE TABLE IF NOT EXISTS incident_registry (
    incident_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('LOW','MEDIUM','HIGH','CRITICAL','UNKNOWN')),
    status TEXT NOT NULL CHECK (status IN ('OPEN','INVESTIGATING','MITIGATED','RESOLVED','CLOSED')),
    classification TEXT NOT NULL DEFAULT 'NOT_VERIFIED',
    opened_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    owner_ref TEXT,
    hypothesis JSONB NOT NULL DEFAULT '[]'::jsonb,
    evidence_ids UUID[] NOT NULL DEFAULT '{}',
    resolution_summary TEXT
);
CREATE INDEX IF NOT EXISTS idx_incident_registry_status_severity
    ON incident_registry (status, severity, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_incident_registry_evidence_ids
    ON incident_registry USING GIN (evidence_ids);

CREATE TABLE IF NOT EXISTS approval_registry (
    approval_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requested_by TEXT NOT NULL,
    approved_by TEXT,
    action TEXT NOT NULL,
    target_ref TEXT NOT NULL,
    scope JSONB NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('PENDING','APPROVED','DENIED','REVOKED','EXPIRED')),
    requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    decided_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    evidence_id UUID REFERENCES evidence_registry(evidence_id),
    CHECK (decision <> 'APPROVED' OR (approved_by IS NOT NULL AND decided_at IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS idx_approval_registry_target_decision
    ON approval_registry (target_ref, decision, requested_at DESC);
CREATE INDEX IF NOT EXISTS idx_approval_registry_evidence
    ON approval_registry (evidence_id);

CREATE TABLE IF NOT EXISTS audit_registry (
    audit_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    actor_identity TEXT NOT NULL,
    action TEXT NOT NULL,
    target_ref TEXT NOT NULL,
    decision TEXT NOT NULL,
    correlation_id TEXT,
    source_revision TEXT,
    evidence_id UUID REFERENCES evidence_registry(evidence_id),
    sanitized_details JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_audit_registry_time
    ON audit_registry (occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_registry_target
    ON audit_registry (target_ref, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_registry_evidence
    ON audit_registry (evidence_id);

CREATE TABLE IF NOT EXISTS production_gate_registry (
    gate_observation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gate_id TEXT NOT NULL CHECK (gate_id ~ '^Q([0-9]{2})$'),
    release_ref TEXT NOT NULL,
    commit_sha CHAR(40),
    tree_sha CHAR(40),
    status TEXT NOT NULL CHECK (status IN ('PASS','FAIL','BLOCKED','NOT_VERIFIED','PASS_CANDIDATE')),
    observed_at TIMESTAMPTZ NOT NULL,
    verifier_identity TEXT,
    evidence_id UUID REFERENCES evidence_registry(evidence_id),
    limitations JSONB NOT NULL DEFAULT '[]'::jsonb,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (commit_sha IS NULL OR commit_sha ~ '^[0-9a-f]{40}$'),
    CHECK (tree_sha IS NULL OR tree_sha ~ '^[0-9a-f]{40}$')
);
CREATE INDEX IF NOT EXISTS idx_gate_release
    ON production_gate_registry (release_ref, gate_id, observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_gate_evidence
    ON production_gate_registry (evidence_id);

-- Append-only intent is enforced by application roles/permissions in deployment.
-- Do not grant UPDATE/DELETE to collector/API roles for audit/evidence records.
-- This migration deliberately does not create users, grants, credentials, or production data.

COMMIT;
