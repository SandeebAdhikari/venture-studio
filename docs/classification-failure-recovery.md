# Classification failure recovery (operational)

This document describes how terminal `failed` classification signals are stored and the safest way to reprocess them after HTML grounding or taxonomy fixes. **There is no automatic retry queue** in the pipeline.

## Where failures become terminal

1. **Validator** (`ClassificationValidator`) — invalid taxonomy codes, missing quote, quote not grounded in source text.
2. **Graph retries exhausted** — `classification_max_retries` attempts; signal set to `failed` with joined validation errors.
3. **Post-LLM persistence** (`ComplaintClassificationService._finalize_signal`) — `taxonomy_resolution_failed` when `resolve_category_ids` cannot map codes to `categories` rows.

Terminal state is persisted on `signals`:

| Column | Value |
|--------|--------|
| `processing_status` | `failed` |
| `skip_reason` | e.g. `verbatim_quote must appear in source text`, `taxonomy_resolution_failed`, `invalid customer_type: employee; ...` |

`classify_pending()` only loads `processing_status = pending`. Failed rows are **not** picked up again unless status is reset or `classify_signal(signal_id)` is invoked directly.

## Direct re-classify API (no status reset)

`ComplaintClassificationService.classify_signal` accepts signals in `pending` **or** `failed`:

```python
# Allowed: PENDING or FAILED
await service.classify_signal(signal_id)
```

Use this for targeted recovery of known IDs after deploying fixes.

## Batch requeue (operational)

To re-run classification for all failures of a given cause:

```sql
-- Preview
SELECT id, skip_reason, collected_at
FROM signals
WHERE processing_status = 'failed'
  AND skip_reason LIKE '%verbatim_quote%';

-- Requeue for classify_pending (clears last failure reason)
UPDATE signals
SET processing_status = 'pending',
    skip_reason = NULL
WHERE processing_status = 'failed'
  AND (
    skip_reason LIKE '%verbatim_quote%'
    OR skip_reason = 'taxonomy_resolution_failed'
  );
```

Then run the pipeline **classify** stage or `classify_pending(limit=N)` until `count_pending()` is zero.

**Do not** reset `skipped` or `classified` signals unless you intend to duplicate complaints (guard: `get_by_signal_id` raises if complaint already exists).

## Prerequisites after taxonomy fix

1. Apply migration `020_taxonomy_other_categories` (adds `domain` and `persona` code `other`).
2. Confirm resolution:

```sql
SELECT code, kind FROM categories WHERE code = 'other';
```

Expected: rows for `complaint_category` (existing), `domain`, and `persona`.

## Expected recovery impact (run bc69e77a audit)

| Failure bucket | Count | Expected after fix |
|----------------|------:|--------------------|
| `verbatim_quote must appear in source text` | 16 | Recoverable via HTML/entity normalization |
| `taxonomy_resolution_failed` (persona/domain `other`) | 7 | Recoverable after seed + requeue |
| `invalid customer_type: employee` | 1 | **Not** recoverable without LLM returning a valid code |
| Other / transient | 0 | — |

**Upper bound:** ~23 of 24 terminal failures may classify on requeue (assuming LLM outputs stable valid enums and grounded quotes).

## Risk assessment

| Action | Risk | Mitigation |
|--------|------|------------|
| Requeue verbatim failures | Low | Grounding rules unchanged; only source normalization improved |
| Requeue taxonomy failures | Low | Codes must exist in DB; `other` seeded to match taxonomy |
| Reset all `failed` blindly | Medium | Review `skip_reason` filter; exclude permanent enum errors |
| Re-classify `classified` | High | Duplicate complaint guard will error |
| Lowering validation | **Not done** | Do not weaken quote or taxonomy checks |

## Invalid enums (e.g. `employee`)

`customer_type` must be in `CUSTOMER_TYPES` (`taxonomy.py`). **`employee` is rejected at validation** before DB resolution — correct behavior. Prompt text now states job titles outside the list are invalid. Requeue will not help until the model returns a allowed code (`developer`, `ops_admin`, `consumer`, `other`, etc.).
