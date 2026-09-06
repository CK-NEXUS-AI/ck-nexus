BEGIN;

CREATE TABLE IF NOT EXISTS knowledge_research_artifacts (
    tenant_id TEXT NOT NULL,
    artifact_id TEXT NOT NULL,
    decision TEXT NOT NULL,
    truth_state TEXT NOT NULL,
    ready_for_analysis BOOLEAN NOT NULL DEFAULT FALSE,
    scope_json JSONB NOT NULL,
    gaps_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, artifact_id),
    CONSTRAINT knowledge_research_artifacts_tenant_nonempty
        CHECK (btrim(tenant_id) <> ''),
    CONSTRAINT knowledge_research_artifacts_id_nonempty
        CHECK (btrim(artifact_id) <> ''),
    CONSTRAINT knowledge_research_artifacts_decision_check
        CHECK (
            decision IN (
                'CONTINUE_RESEARCH',
                'READY_FOR_ANALYSIS',
                'HUMAN_REVIEW_REQUIRED'
            )
        ),
    CONSTRAINT knowledge_research_artifacts_truth_state_check
        CHECK (
            truth_state IN (
                'DISCOVERED',
                'PLANNED',
                'EXECUTED',
                'MEASURED',
                'REVIEW_REQUIRED',
                'MEASURED_NOT_VERIFIED',
                'BLOCKED',
                'FAILED'
            )
        )
);

CREATE INDEX IF NOT EXISTS knowledge_research_artifacts_decision_idx
    ON knowledge_research_artifacts (tenant_id, decision, created_at DESC);

CREATE TABLE IF NOT EXISTS knowledge_research_artifact_sources (
    tenant_id TEXT NOT NULL,
    artifact_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    PRIMARY KEY (tenant_id, artifact_id, source_id),
    CONSTRAINT knowledge_research_artifact_sources_artifact_fk
        FOREIGN KEY (tenant_id, artifact_id)
        REFERENCES knowledge_research_artifacts (tenant_id, artifact_id)
        ON DELETE CASCADE,
    CONSTRAINT knowledge_research_artifact_sources_source_fk
        FOREIGN KEY (tenant_id, source_id)
        REFERENCES knowledge_sources (tenant_id, source_id)
        ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS knowledge_research_artifact_sources_source_idx
    ON knowledge_research_artifact_sources (tenant_id, source_id, artifact_id);

CREATE TABLE IF NOT EXISTS knowledge_research_artifact_claims (
    tenant_id TEXT NOT NULL,
    artifact_id TEXT NOT NULL,
    claim_id TEXT NOT NULL,
    PRIMARY KEY (tenant_id, artifact_id, claim_id),
    CONSTRAINT knowledge_research_artifact_claims_artifact_fk
        FOREIGN KEY (tenant_id, artifact_id)
        REFERENCES knowledge_research_artifacts (tenant_id, artifact_id)
        ON DELETE CASCADE,
    CONSTRAINT knowledge_research_artifact_claims_claim_fk
        FOREIGN KEY (tenant_id, claim_id)
        REFERENCES knowledge_claims (tenant_id, claim_id)
        ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS knowledge_research_artifact_claims_claim_idx
    ON knowledge_research_artifact_claims (tenant_id, claim_id, artifact_id);

CREATE TABLE IF NOT EXISTS knowledge_research_lineage_edges (
    tenant_id TEXT NOT NULL,
    artifact_id TEXT NOT NULL,
    edge_id TEXT NOT NULL,
    from_node_kind TEXT NOT NULL,
    from_node_id TEXT NOT NULL,
    to_node_kind TEXT NOT NULL,
    to_node_id TEXT NOT NULL,
    edge_type TEXT NOT NULL,
    independent_validation BOOLEAN NOT NULL DEFAULT FALSE,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, artifact_id, edge_id),
    CONSTRAINT knowledge_research_lineage_edges_artifact_fk
        FOREIGN KEY (tenant_id, artifact_id)
        REFERENCES knowledge_research_artifacts (tenant_id, artifact_id)
        ON DELETE CASCADE,
    CONSTRAINT knowledge_research_lineage_edges_from_kind_check
        CHECK (from_node_kind IN ('SOURCE', 'CLAIM')),
    CONSTRAINT knowledge_research_lineage_edges_to_kind_check
        CHECK (to_node_kind IN ('SOURCE', 'CLAIM')),
    CONSTRAINT knowledge_research_lineage_edges_type_check
        CHECK (
            edge_type IN (
                'CITES',
                'DERIVED_FROM',
                'SUPPORTS',
                'CONTRADICTS'
            )
        ),
    CONSTRAINT knowledge_research_lineage_edges_not_self
        CHECK (
            from_node_kind <> to_node_kind
            OR from_node_id <> to_node_id
        )
);

CREATE TABLE IF NOT EXISTS knowledge_research_contradictions (
    tenant_id TEXT NOT NULL,
    artifact_id TEXT NOT NULL,
    contradiction_id TEXT NOT NULL,
    contradiction_type TEXT NOT NULL,
    resolution_status TEXT NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    claim_ids JSONB NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, artifact_id, contradiction_id),
    CONSTRAINT knowledge_research_contradictions_artifact_fk
        FOREIGN KEY (tenant_id, artifact_id)
        REFERENCES knowledge_research_artifacts (tenant_id, artifact_id)
        ON DELETE CASCADE,
    CONSTRAINT knowledge_research_contradictions_type_check
        CHECK (
            contradiction_type IN (
                'FACTUAL',
                'TEMPORAL',
                'LOGICAL_REVIEW_REQUIRED'
            )
        ),
    CONSTRAINT knowledge_research_contradictions_status_check
        CHECK (
            resolution_status IN (
                'UNRESOLVED',
                'RESEARCH_REQUIRED',
                'HUMAN_REVIEW_REQUIRED',
                'RESOLVED'
            )
        ),
    CONSTRAINT knowledge_research_contradictions_confidence_check
        CHECK (confidence >= 0.0 AND confidence <= 1.0)
);

CREATE TABLE IF NOT EXISTS knowledge_research_search_attempts (
    tenant_id TEXT NOT NULL,
    artifact_id TEXT NOT NULL,
    attempt_id TEXT NOT NULL,
    query TEXT NOT NULL,
    engine TEXT NOT NULL,
    result_count INTEGER NOT NULL,
    duration_ms INTEGER,
    status TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, artifact_id, attempt_id),
    CONSTRAINT knowledge_research_search_attempts_artifact_fk
        FOREIGN KEY (tenant_id, artifact_id)
        REFERENCES knowledge_research_artifacts (tenant_id, artifact_id)
        ON DELETE CASCADE,
    CONSTRAINT knowledge_research_search_attempts_query_nonempty
        CHECK (btrim(query) <> ''),
    CONSTRAINT knowledge_research_search_attempts_result_count_check
        CHECK (result_count >= 0),
    CONSTRAINT knowledge_research_search_attempts_duration_check
        CHECK (duration_ms IS NULL OR duration_ms >= 0)
);

CREATE INDEX IF NOT EXISTS knowledge_research_search_attempts_engine_idx
    ON knowledge_research_search_attempts (
        tenant_id,
        engine,
        created_at DESC
    );

CREATE TABLE IF NOT EXISTS knowledge_research_coverage_metrics (
    tenant_id TEXT NOT NULL,
    artifact_id TEXT NOT NULL,
    metric_id TEXT NOT NULL,
    dimension TEXT NOT NULL,
    coverage_fraction DOUBLE PRECISION,
    scoped BOOLEAN NOT NULL DEFAULT TRUE,
    payload JSONB NOT NULL,
    measured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, artifact_id, metric_id),
    CONSTRAINT knowledge_research_coverage_metrics_artifact_fk
        FOREIGN KEY (tenant_id, artifact_id)
        REFERENCES knowledge_research_artifacts (tenant_id, artifact_id)
        ON DELETE CASCADE,
    CONSTRAINT knowledge_research_coverage_metrics_dimension_nonempty
        CHECK (btrim(dimension) <> ''),
    CONSTRAINT knowledge_research_coverage_metrics_fraction_check
        CHECK (
            coverage_fraction IS NULL
            OR (
                coverage_fraction >= 0.0
                AND coverage_fraction <= 1.0
            )
        )
);

CREATE INDEX IF NOT EXISTS knowledge_research_coverage_metrics_dimension_idx
    ON knowledge_research_coverage_metrics (
        tenant_id,
        dimension,
        measured_at DESC
    );

COMMIT;
