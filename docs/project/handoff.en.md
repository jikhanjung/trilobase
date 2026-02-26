# Project Handoff

**Last updated:** 2026-02-25

## Project Overview

A trilobite taxonomic database project. Genus data extracted from Jell & Adrain (2002) PDF is cleaned, normalized, and distributed as a SCODA package.

- **SCODA Engine** (runtime): separate repo (`scoda-engine`)
- **Completed phases**: 1–46

## Current Status

| Item | Value |
|------|-------|
| Phases completed | 1–46 (all done) |
| Trilobase version | 0.2.3 |
| PaleoCore version | 0.1.1 |
| taxonomic_ranks | 5,341 records |
| Valid genera | 4,259 (83.3%) |
| Invalid genera | 856 (16.7%) |
| Synonym linkage | 99.9% (1,054/1,055) |
| Taxonomic opinions | 84 (PLACED_IN 82 + SPELLING_OF 2) |
| Tests | 101 passing |

## Database Tables

### Canonical DB (trilobase.db)

| Table/View | Records | Description |
|------------|---------|-------------|
| taxonomic_ranks | 5,341 | Unified taxonomy (Class–Genus) |
| synonyms | 1,055 | Synonym relationships |
| genus_formations | 4,853 | Genus–Formation links |
| genus_locations | 4,841 | Genus–Country links |
| bibliography | 2,130 | Literature references |
| taxon_bibliography | 4,040 | Taxon↔Bibliography FK links |
| taxonomic_opinions | 84 | Taxonomic opinions |
| taxa (view) | 5,113 | Backward-compatibility view |
| artifact_metadata | 7 | SCODA artifact metadata |
| provenance | 5 | Data provenance |
| schema_descriptions | 112 | Table/column descriptions |
| ui_display_intent | 6 | SCODA view type hints |
| ui_queries | 37 | Named SQL queries |
| ui_manifest | 1 | Declarative view definitions |

### Overlay DB (trilobase_overlay.db)

| Table | Records | Description |
|-------|---------|-------------|
| overlay_metadata | 2 | Canonical DB version tracking |
| user_annotations | 0 | User annotations |

## CI/CD

| Workflow | Trigger | Action |
|----------|---------|--------|
| `ci.yml` | push/PR to main | Automated pytest |
| `release.yml` | tag `v*.*.*` push | pytest → .scoda build → Hub Manifest → GitHub Release |
| `manual-release.yml` | workflow_dispatch | Manual release (same pipeline) |

## Open Issues

- **1 unlinked synonym**: Szechuanella — preoccupied, not replaced
- **257 parent_id NULL**: all invalid genera (normal)
- **1 valid genus without temporal_code**: Dignagnostus — no code in source
- **~30 Chinese romanization hyphens**: possible Wade-Giles notation, deferred
