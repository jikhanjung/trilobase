# T-4: Synonyms → Taxonomic Opinions Migration

**Date:** 2026-02-27
**Type:** Implementation
**Plan:** `devlog/20260227_P70_synonym_migration_plan.md`

## Summary

Migrated 1,055 synonym records from the `synonyms` table into `taxonomic_opinions` as `SYNONYM_OF` opinions. The `synonyms` table is now a backward-compatible VIEW. This completes the unification of all taxonomic assertions into the `taxonomic_opinions` table.

## Changes

### Schema Changes

| Change | Detail |
|--------|--------|
| `taxonomic_opinions.synonym_type` | New column: `j.s.s.`, `j.o.s.`, `preocc.`, `replacement`, `suppressed` (NULL for non-SYNONYM_OF) |
| `taxon_bibliography.synonym_id` | Renamed → `opinion_id` (FK to `taxonomic_opinions.id`) |
| `synonyms` table | Replaced with backward-compatible VIEW |

### Record Counts

| Item | Before | After |
|------|--------|-------|
| `synonyms` table | 1,055 records | VIEW (1,055 rows from opinions) |
| `taxonomic_opinions` | 84 records | 1,139 records |
| `taxon_bibliography.opinion_id` | (was `synonym_id` 433) | 433 rows |

### Opinion Type Breakdown (Post-Migration)

| Type | Count |
|------|-------|
| SYNONYM_OF | 1,055 |
| PLACED_IN | 82 |
| SPELLING_OF | 2 |
| **Total** | **1,139** |

### SYNONYM_OF Distribution

| synonym_type | Count |
|--------------|-------|
| j.s.s. | 721 |
| preocc. | 146 |
| replacement | 125 |
| j.o.s. | 54 |
| suppressed | 9 |

### is_accepted Logic

- 1,012 taxa have exactly 1 SYNONYM_OF opinion (is_accepted=1)
- 43 taxa have 2 synonym records each (multi-synonym)
  - Priority: j.s.s. > j.o.s. > suppressed > replacement > preocc.
  - Highest priority → is_accepted=1; others → is_accepted=0

### fide → bibliography_id

- 433 fide matches preserved from `taxon_bibliography` (already linked by `link_bibliography.py`)
- 287 records with fide_author but no bibliography match: "fide AUTHOR, YEAR" preserved in `notes`

### Szechuanella (syn 960)

- Preoccupied, not replaced: `related_taxon_id = NULL` (allowed by schema)
- Notes preserved explaining the situation

## Files Modified

| File | Change |
|------|--------|
| `scripts/migrate_synonyms_to_opinions.py` | **New** — migration script (--dry-run, --verify) |
| `tests/conftest.py` | Remove synonyms table, add synonym_type, opinion_id, synonyms VIEW |
| `tests/test_trilobase.py` | Update synonym_id→opinion_id, add 7 SYNONYM_OF tests, update count |
| `scripts/add_scoda_ui_tables.py` | Rewrite genus_synonyms query to use taxonomic_opinions |
| `scripts/add_scoda_tables.py` | Update synonyms description (VIEW) |
| `scripts/add_opinions_schema.py` | Add synonym_type to taxon_opinions query |
| `scripts/link_bibliography.py` | synonym_id→opinion_id, detect column dynamically |
| `scripts/fix_spelling_variants.py` | Remove synonyms FK safety check |
| `spa/index.html` | Handle nullable fide_author (fallback to notes) |
| `db/trilobase.db` | Migration applied |

## Tests

- 108 passing (was 101; +7 new SYNONYM_OF tests)
- All existing tests continue to pass
