# Changelog — PaleoCore

All notable changes to the **paleocore** package will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html):
**Major** = schema change, **Minor** = significant data addition, **Patch** = data quality fix.

## [Unreleased]

## [0.1.1] - 2026-02-21

### Changed
- `formations` table: `country` and `period` columns populated (99.65% and 98.6% coverage)
- `formation_detail` query: added country and period JOIN links

### Fixed
- `countries` data quality: 151 → 142 entries (parsing error 1, duplicate/typo merges 8, prefix normalization 4)
- `geographic_regions`: 4 UID inconsistencies resolved (synced with countries)

## [0.1.0] - 2026-02-13

### Added
- Initial release
- `countries` table — 142 records (ISO 3166-1 mapped)
- `geographic_regions` table — 562 records (hierarchical: 60 countries + 502 regions)
- `formations` table — 2,004 geological formations
- `temporal_ranges` table — 28 time period codes
- `ics_chronostrat` table — 178 ICS chronostratigraphic units (GTS 2020)
- `temporal_ics_mapping` table — 40 temporal code ↔ ICS mappings
- `cow_states` table — 244 COW state system records
- `country_cow_mapping` table — 142 country ↔ COW mappings (96.5%)
- SCODA metadata: `artifact_metadata`, `provenance`, `schema_descriptions`
- SCODA UI: `ui_display_intent`, `ui_queries`, `ui_manifest`
