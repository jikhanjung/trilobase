# Changelog — Trilobase

All notable changes to the **trilobase** package will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html):
**Major** = schema change, **Minor** = significant data addition, **Patch** = data quality fix.

## [Unreleased]

## [0.2.2] - 2026-02-22

### Added
- Agnostina Suborder (id=5344) under Agnostida Order — conventional taxonomy placement
- `questionable` assertion_status for `?FAMILY`/`??FAMILY` genera (32 opinions)
- `incertae_sedis` opinions for FAMILY UNCERTAIN genera (22 opinions)
- `indet` opinions for INDET genera (14 opinions)
- Conventional placement opinions for 10 Agnostida families under Agnostina (10 opinions)

### Changed
- Valid genera parent_id NULL: 68 → 0 (all resolved)
- Agnostida 10 families reparented: Order → Agnostina Suborder
- Total taxonomic opinions: 6 → 84 (PLACED_IN 82 + SPELLING_OF 2)
- taxonomic_ranks: 5,340 → 5,341 (+1 Agnostina Suborder)

### Removed
- `scripts/validate_manifest.py` — migrated to `scoda_engine_core` (P10)

## [0.2.1] - 2026-02-22

### Added
- `SPELLING_OF` opinion type — orthographic variant tracking (2 records)
- `is_placeholder` column in `taxonomic_ranks` — placeholder entries for Agnostida Order (2 records)
- `scripts/fill_temporal_codes.py` — temporal_code auto-fill from raw_entry

### Changed
- Agnostida opinions restructured: family-level → order-level (4 PLACED_IN opinions)
- `temporal_code` populated for 84 of 85 genera missing codes (1 has no code in source)
- Total taxonomic opinions: 2 → 6 (PLACED_IN 4 + SPELLING_OF 2)

## [0.2.0] - 2026-02-21

### Added
- `taxon_bibliography` junction table — 4,040 FK links (original_description 3,607 + fide 433)
- `taxonomic_opinions` table — classification opinion tracking with 4-trigger pattern (B-1 PoC, 2 records)
- Named queries: `taxon_bibliography_list`, `taxon_bibliography`, `get_taxon_opinions`
- Manifest detail views updated: `bibliography_detail`, `genus_detail`, `rank_detail` now include bibliography/opinion sections
- MCP tool: `get_taxon_opinions` (dynamic, via mcp_tools_trilobase.json)
- `CHANGELOG.md` included in `.scoda` package
- `scripts/bump_version.py` — version management script

### Changed
- Synonym linkage improved: 24 unlinked → 1 (97.6% → 99.9%)
- parent_id NULL valid genera reduced: 85 → 68 (13 genera linked to correct families)
- Valid genus count adjusted: 4,260 → 4,259 (1 reclassified as invalid)
- Invalid genus count adjusted: 855 → 856

### Fixed
- PDF line-break hyphen removal: 165 patterns (149 unique) across taxon names, species epithets, and place names
- Source data whitespace fixes: 44 cases (missing spaces around in/et/&)
- Encoding fixes: BRAÑA encoding 13 cases, control character removal 2 cases
- Colon → semicolon corrections: 4 cases
- Spelling corrections: Grinellaspis, Bailliella, Parakoldinoidia, Tschernyschewella
- CHU-GAEVA → CHUGAEVA normalization
- Paraacidaspis duplicate resolution

## [0.1.0] - 2026-02-07

### Added
- Initial release
- `taxonomic_ranks` table — 5,340 records (Class through Genus)
- `synonyms` table — 1,055 synonym relationships
- `genus_formations` table — 4,853 genus-formation links
- `genus_locations` table — 4,841 genus-country links
- `bibliography` table — 2,130 literature references
- `taxa` compatibility view
- SCODA metadata: `artifact_metadata`, `provenance`, `schema_descriptions`
- SCODA UI: `ui_display_intent`, `ui_queries`, `ui_manifest`
- Dependency on `paleocore` package (geographic/stratigraphic reference data)
