# Project History

This page documents the completed development phases (1–46) of the Trilobase project.

The full detailed history is available in the [Korean version](history.md) of this page.

---

## Phase Summary

| Phase | Date | Description |
|-------|------|-------------|
| 1–7 | 2026-02-04 | Data cleaning and DB construction |
| 8–12 | 2026-02-05 | DB consolidation, web UI, bibliography |
| 13–17 | 2026-02-06 | SCODA core, MCP planning |
| 18–22 | 2026-02-07–09 | SCODA implementation, Flask→FastAPI migration, MCP server |
| 23–27 | 2026-02-10–12 | PaleoCore separation, overlay system, SPA |
| 28–32 | 2026-02-12–13 | PaleoCore package, SCODA packaging |
| 33–37 | 2026-02-14–17 | Data quality fixes (hyphenation, encoding, synonyms) |
| 38–40 | 2026-02-18–19 | PyInstaller builds, CI/CD setup |
| 41–43 | 2026-02-20–21 | Bibliography FK links, taxonomic opinions |
| 44–46 | 2026-02-22–24 | Agnostida restructuring, UI fixes, data integrity |

---

## Key Milestones

- **Phase 1**: Initial text extraction and normalization from Jell & Adrain (2002) PDF
- **Phase 8**: Unified `taxonomic_ranks` table consolidation
- **Phase 13**: SCODA core tables (artifact_metadata, provenance, schema_descriptions)
- **Phase 22**: MCP server with 14 tools for LLM integration
- **Phase 28**: PaleoCore package separation (8 tables moved)
- **Phase 33**: SCODA package format (.scoda ZIP distribution)
- **Phase 40**: CI/CD pipeline (GitHub Actions: ci, release, manual-release)
- **Phase 41**: Bibliography FK linkage (4,040 taxon↔bibliography links)
- **Phase 44**: Complete parent_id resolution for all valid genera
