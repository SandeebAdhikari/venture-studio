-- FF-CM-5 shadow-mode verification queries (informational only; no migrations).

-- Coverage: entries with capability_match_score key present (including null values).
SELECT COUNT(*)
FROM executive_ranking_entries
WHERE ranking_details ? 'capability_match_score';

-- Fingerprint coverage: entries with a resolved dominant fingerprint.
SELECT COUNT(*)
FROM executive_ranking_entries
WHERE ranking_details->>'dominant_fingerprint' IS NOT NULL;

-- Gap distribution: critical gap count per entry.
SELECT
  jsonb_array_length(
    COALESCE(
      ranking_details->'critical_gaps',
      '[]'::jsonb
    )
  ) AS critical_gap_count,
  COUNT(*) AS entry_count
FROM executive_ranking_entries
WHERE ranking_details ? 'capability_match_shadow'
GROUP BY 1
ORDER BY 1;
