DROP TABLE IF EXISTS place_state_mentions;
DROP TABLE IF EXISTS sentence_place_state_reviews;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'place_survival_model_runs'
          AND column_name = 'label_prompt_version'
    ) AND NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'place_survival_model_runs'
          AND column_name = 'label_source_version'
    ) THEN
        ALTER TABLE place_survival_model_runs
            RENAME COLUMN label_prompt_version TO label_source_version;
    END IF;
END $$;
