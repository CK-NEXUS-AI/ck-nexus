BEGIN;

CREATE TABLE IF NOT EXISTS knowledge_sources (
    tenant_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    source_hash TEXT,
    source_version TEXT,
    payload JSONB NOT NULL,
    revoked BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, source_id),
    CONSTRAINT knowledge_sources_tenant_nonempty CHECK (btrim(tenant_id) <> ''),
    CONSTRAINT knowledge_sources_id_nonempty CHECK (btrim(source_id) <> '')
);

CREATE UNIQUE INDEX IF NOT EXISTS knowledge_sources_version_identity_idx
    ON knowledge_sources (tenant_id, source_id, source_version)
    WHERE source_version IS NOT NULL;

CREATE INDEX IF NOT EXISTS knowledge_sources_hash_idx
    ON knowledge_sources (tenant_id, source_hash)
    WHERE source_hash IS NOT NULL;

CREATE INDEX IF NOT EXISTS knowledge_sources_active_idx
    ON knowledge_sources (tenant_id, revoked, source_id);

CREATE TABLE IF NOT EXISTS knowledge_claims (
    tenant_id TEXT NOT NULL,
    claim_id TEXT NOT NULL,
    subject TEXT NOT NULL,
    predicate TEXT NOT NULL,
    claim_class TEXT NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL,
    fresh_until TIMESTAMPTZ,
    confidence DOUBLE PRECISION NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, claim_id),
    CONSTRAINT knowledge_claims_tenant_nonempty CHECK (btrim(tenant_id) <> ''),
    CONSTRAINT knowledge_claims_id_nonempty CHECK (btrim(claim_id) <> ''),
    CONSTRAINT knowledge_claims_subject_nonempty CHECK (btrim(subject) <> ''),
    CONSTRAINT knowledge_claims_predicate_nonempty CHECK (btrim(predicate) <> ''),
    CONSTRAINT knowledge_claims_class_check CHECK (
        claim_class IN ('fact', 'opinion', 'inference', 'prediction', 'assumption')
    ),
    CONSTRAINT knowledge_claims_confidence_check CHECK (
        confidence >= 0.0 AND confidence <= 1.0
    )
);

CREATE INDEX IF NOT EXISTS knowledge_claims_lookup_idx
    ON knowledge_claims (tenant_id, subject, predicate, observed_at DESC);

CREATE INDEX IF NOT EXISTS knowledge_claims_freshness_idx
    ON knowledge_claims (tenant_id, fresh_until)
    WHERE fresh_until IS NOT NULL;

CREATE TABLE IF NOT EXISTS knowledge_claim_sources (
    tenant_id TEXT NOT NULL,
    claim_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    PRIMARY KEY (tenant_id, claim_id, source_id),
    CONSTRAINT knowledge_claim_sources_claim_fk
        FOREIGN KEY (tenant_id, claim_id)
        REFERENCES knowledge_claims (tenant_id, claim_id)
        ON DELETE CASCADE,
    CONSTRAINT knowledge_claim_sources_source_fk
        FOREIGN KEY (tenant_id, source_id)
        REFERENCES knowledge_sources (tenant_id, source_id)
        ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS knowledge_claim_sources_source_idx
    ON knowledge_claim_sources (tenant_id, source_id, claim_id);

CREATE TABLE IF NOT EXISTS knowledge_claim_relations (
    tenant_id TEXT NOT NULL,
    claim_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    related_claim_id TEXT NOT NULL,
    PRIMARY KEY (tenant_id, claim_id, relation_type, related_claim_id),
    CONSTRAINT knowledge_claim_relations_type_check CHECK (
        relation_type IN ('contradicts', 'supersedes')
    ),
    CONSTRAINT knowledge_claim_relations_not_self CHECK (claim_id <> related_claim_id),
    CONSTRAINT knowledge_claim_relations_claim_fk
        FOREIGN KEY (tenant_id, claim_id)
        REFERENCES knowledge_claims (tenant_id, claim_id)
        ON DELETE CASCADE,
    CONSTRAINT knowledge_claim_relations_related_fk
        FOREIGN KEY (tenant_id, related_claim_id)
        REFERENCES knowledge_claims (tenant_id, claim_id)
        ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS knowledge_claim_relations_related_idx
    ON knowledge_claim_relations (tenant_id, related_claim_id, relation_type);

CREATE TABLE IF NOT EXISTS knowledge_memory_proposals (
    tenant_id TEXT NOT NULL,
    proposal_id TEXT NOT NULL,
    retention_class TEXT NOT NULL,
    retention_days INTEGER NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, proposal_id),
    CONSTRAINT knowledge_memory_proposals_tenant_nonempty CHECK (btrim(tenant_id) <> ''),
    CONSTRAINT knowledge_memory_proposals_id_nonempty CHECK (btrim(proposal_id) <> ''),
    CONSTRAINT knowledge_memory_proposals_retention_days_check CHECK (retention_days > 0),
    CONSTRAINT knowledge_memory_proposals_retention_class_check CHECK (
        retention_class IN (
            'EPHEMERAL',
            'SESSION',
            'OPERATIONAL',
            'LONG_TERM',
            'USER_PINNED',
            'LEGAL_HOLD'
        )
    )
);

CREATE INDEX IF NOT EXISTS knowledge_memory_proposals_retention_idx
    ON knowledge_memory_proposals (tenant_id, retention_class, created_at);

CREATE TABLE IF NOT EXISTS knowledge_memory_proposal_claims (
    tenant_id TEXT NOT NULL,
    proposal_id TEXT NOT NULL,
    claim_id TEXT NOT NULL,
    PRIMARY KEY (tenant_id, proposal_id, claim_id),
    CONSTRAINT knowledge_memory_proposal_claims_proposal_fk
        FOREIGN KEY (tenant_id, proposal_id)
        REFERENCES knowledge_memory_proposals (tenant_id, proposal_id)
        ON DELETE CASCADE,
    CONSTRAINT knowledge_memory_proposal_claims_claim_fk
        FOREIGN KEY (tenant_id, claim_id)
        REFERENCES knowledge_claims (tenant_id, claim_id)
        ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS knowledge_memory_proposal_claims_claim_idx
    ON knowledge_memory_proposal_claims (tenant_id, claim_id, proposal_id);

COMMIT;
