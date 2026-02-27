# Post-Migration Fix: Synonym Manifest & Fide Linking

**Date:** 2026-02-27
**Type:** Implementation
**Follows:** `devlog/20260227_096_synonym_migration.md`

## Summary

Fixed two issues discovered after the T-4 synonym migration:
1. Synonymy section not rendering in genus_detail
2. 133 additional fide→bibliography links resolved

## Issue 1: Synonymy Section Empty in Genus Detail

**Symptom:** genus_detail showed empty Synonymy section despite data existing in DB.

**Root causes:**
- `genus_detail` manifest `sub_queries` was missing `synonyms` entry — engine never fetched the data
- `synonym_list` section type has no renderer in scoda-engine `app.js` — fallback to `renderLinkedTable` requires `columns` definition

**Fix:**
- Added `synonyms` sub_query to `genus_detail` manifest (script + DB)
- Changed section type `synonym_list` → `linked_table` with explicit columns: Type, Senior Synonym (linked), Fide, Year

### Files Modified

| File | Change |
|------|--------|
| `scripts/add_scoda_manifest.py` | Added `synonyms` sub_query; `synonym_list` → `linked_table` with columns |
| `db/trilobase.db` | Manifest updated directly |

## Issue 2: Unmatched Fide → Bibliography Links

**Symptom:** Austrosinia showed "fide ZAN, 1992" in Synonymy but ZAN 1992 missing from Bibliography section.

**Root cause:** Migration script's fide matching was too simple — failed on `et al.`, year suffixes (`1958a`), and initial-prefixed surnames (`W. ZHANG`).

**Fix:**
1. Improved fide author matching: handle `et al.`, year suffixes, initial prefixes
2. Linked `taxonomic_opinions.bibliography_id` for 133 newly matched opinions
3. Inserted 133 corresponding `taxon_bibliography` fide entries

### Matching Results

| Category | Count |
|----------|-------|
| Previously matched (migration) | 433 |
| Newly matched (this fix) | 133 |
| **Total linked** | **566** |
| Remaining unmatched | 154 |
| — "fide JELL/ADRAIN, herein" | ~30 (no year, unparseable) |
| — No bibliography entry found | ~124 |

### Record Counts

| Table | Before | After |
|-------|--------|-------|
| `taxon_bibliography` | 4,040 | 4,173 (+133 fide) |
| `taxonomic_opinions` with `bibliography_id` | 433 | 566 (+133) |

## Version

Bumped to 0.2.4. CHANGELOG `[Unreleased]` → `[0.2.4] - 2026-02-27`.
