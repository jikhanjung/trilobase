# P70: T-4 Synonyms → Taxonomic Opinions Migration Plan

**Date:** 2026-02-27
**Type:** Plan
**Status:** Completed (see `20260227_096_synonym_migration.md`)

## Summary

Plan to migrate 1,055 synonym records from the `synonyms` table into `taxonomic_opinions` as `SYNONYM_OF` opinions. Adds `synonym_type` column to opinions, rebuilds `taxon_bibliography` with `opinion_id`, creates backward-compatible `synonyms` VIEW.

See implementation devlog for full details.
