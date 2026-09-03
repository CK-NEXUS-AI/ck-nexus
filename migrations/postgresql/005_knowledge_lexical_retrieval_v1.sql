BEGIN;

CREATE INDEX IF NOT EXISTS knowledge_claims_lexical_fts_idx
    ON knowledge_claims
    USING GIN (
        to_tsvector(
            'simple'::regconfig,
            subject || ' ' || predicate || ' ' ||
            COALESCE(payload ->> 'value', '')
        )
    );

COMMIT;
