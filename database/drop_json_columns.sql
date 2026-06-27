BEGIN;

ALTER TABLE sentence_udpipe_tokens
    DROP COLUMN IF EXISTS feats,
    DROP COLUMN IF EXISTS deps,
    DROP COLUMN IF EXISTS misc;

ALTER TABLE sentence_trankit_tokens
    DROP COLUMN IF EXISTS feats,
    DROP COLUMN IF EXISTS deps,
    DROP COLUMN IF EXISTS misc;

ALTER TABLE sentence_llm_grammar_analyses
    DROP COLUMN IF EXISTS response_json;

ALTER TABLE sentence_llm_grammar_tokens
    DROP COLUMN IF EXISTS feats;

ALTER TABLE manto_releases
    DROP COLUMN IF EXISTS metadata;

ALTER TABLE manto_raw_records
    DROP COLUMN IF EXISTS data;

ALTER TABLE manto_entities
    DROP COLUMN IF EXISTS data;

ALTER TABLE manto_edges
    DROP COLUMN IF EXISTS data;

ALTER TABLE manto_place_network_features
    DROP COLUMN IF EXISTS features;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND data_type IN ('json', 'jsonb')
    ) THEN
        RAISE EXCEPTION 'PostgreSQL JSON/JSONB columns remain in public schema';
    END IF;
END $$;

COMMIT;
