-- Read-only planning audit, 9 November 2026.
-- Use an explicitly configured current production or authorized replica DSN.
-- Do not use initialize_schema(), and do not reopen a retired database.
-- Executed against the documented PG18 endpoint; no data/schema writes.
BEGIN READ ONLY;
SET LOCAL statement_timeout = '20s';
SELECT current_database(), current_user, current_setting('port'),
       current_setting('server_version'), current_setting('transaction_read_only');
SELECT record_id, version, file_key, import_status, imported_at
FROM manto_releases ORDER BY record_id DESC LIMIT 5;
SELECT release_record_id, count(*) AS entities
FROM manto_entities GROUP BY 1 ORDER BY 1;
SELECT release_record_id, is_pre_pausanias, excluded_reason, count(*) AS edges
FROM manto_edges GROUP BY 1,2,3 ORDER BY 1,2,3;
SELECT count(*) AS place_entities,
       count(*) FILTER (WHERE NULLIF(d.pleiades_id, '') IS NOT NULL) AS with_pleiades,
       count(*) FILTER (WHERE p.representative_latitude IS NOT NULL
                         AND p.representative_longitude IS NOT NULL) AS with_coordinates
FROM manto_entity_details d
LEFT JOIN pleiades_places p ON p.pleiades_id = d.pleiades_id
WHERE d.release_record_id = 22239985 AND d.name LIKE '🌍%';
SELECT release_record_id, target_label, count(*)
FROM manto_place_status_labels GROUP BY 1,2 ORDER BY 1,2;
SELECT match_method, confidence, reviewed, count(*) AS rows,
       count(DISTINCT manto_id) AS manto_places
FROM manto_place_links WHERE release_record_id = 22239985
GROUP BY 1,2,3 ORDER BY 1,2,3;
SELECT count(*) AS names_with_multiple_targets
FROM (SELECT reference_form, entity_type FROM manto_place_links
      WHERE release_record_id = 22239985 GROUP BY 1,2
      HAVING count(DISTINCT manto_id) > 1) s;
SELECT release_record_id, feature_set_version, sample_count, positive_count,
       negative_count, balanced_accuracy, status, completed_at
FROM place_survival_model_runs
ORDER BY completed_at DESC NULLS LAST LIMIT 8;
SELECT 'passage' AS source, target_label, temporal_scope, count(*) AS claims,
       count(DISTINCT canonical_place_name) AS distinct_names
FROM passage_place_state_mentions GROUP BY 2,3 ORDER BY 2,3;
SELECT feature_set_version, count(DISTINCT manto_id) AS places
FROM manto_place_connectedness_features
WHERE release_record_id = 22239985 GROUP BY 1;
SELECT count(*) AS model_runs_on_latest_import
FROM place_survival_model_runs WHERE release_record_id = 22239985;
SELECT reference_form, english_transcription, manto_id, manto_label,
       match_method, confidence
FROM manto_place_links
WHERE release_record_id = 22239985
  AND (english_transcription IN ('Aegae', 'Aegina') OR manto_label ILIKE '%Aigai%')
ORDER BY reference_form, manto_label LIMIT 14;
ROLLBACK;
