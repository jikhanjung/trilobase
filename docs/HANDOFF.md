# Trilobase Project Handover

**Last updated:** 2026-02-22

## Project Overview

A trilobite taxonomic database project. Genus data extracted from Jell & Adrain (2002) PDF is cleaned, normalized, and distributed as a SCODA package.

- **SCODA Engine** (runtime): separate repo at `/mnt/d/projects/scoda-engine` (`pip install -e /mnt/d/projects/scoda-engine[dev]`)
- **Completed Phase 1~46 details**: see [HISTORY.md](HISTORY.md)

## Current Status

| Item | Value |
|------|-------|
| Phases completed | 1~46 (all done) |
| Trilobase version | 0.2.0 |
| PaleoCore version | 0.1.1 |
| taxonomic_ranks | 5,340 records (Class~Genus + 2 placeholders) |
| Valid genera | 4,259 (83.3%) |
| Invalid genera | 856 (16.7%) |
| Synonym linkage | 99.9% (1,054/1,055) |
| Taxonomic opinions | 6 (PLACED_IN 4 + SPELLING_OF 2) |
| Tests | 100 passing |

## Database Status

**Canonical DB (trilobase.db) — read-only, immutable:**

| Table/View | Records | Description |
|------------|---------|-------------|
| taxonomic_ranks | 5,340 | Unified taxonomy (Class~Genus) + 2 placeholders |
| synonyms | 1,055 | Synonym relationships |
| genus_formations | 4,853 | Genus-Formation many-to-many |
| genus_locations | 4,841 | Genus-Country many-to-many |
| bibliography | 2,130 | Literature Cited references |
| taxon_bibliography | 4,040 | Taxon↔Bibliography FK links |
| taxonomic_opinions | 6 | Taxonomic opinions (PLACED_IN 4 + SPELLING_OF 2) |
| taxa (view) | 5,113 | Backward-compatibility view |
| artifact_metadata | 7 | SCODA artifact metadata |
| provenance | 5 | Data provenance |
| schema_descriptions | 112 | Table/column descriptions |
| ui_display_intent | 6 | SCODA view type hints |
| ui_queries | 36 | Named SQL queries |
| ui_manifest | 1 | Declarative view definitions (JSON) |

**Overlay DB (trilobase_overlay.db) — read/write, user-local data:**

| Table | Records | Description |
|-------|---------|-------------|
| overlay_metadata | 2 | Canonical DB version tracking (canonical_version, created_at) |
| user_annotations | 0 | User annotations (Local Overlay) |

## Next Tasks

**Roadmap:** `devlog/20260219_P63_future_roadmap.md`

### Data Quality

- ~~T-3a: Fill temporal_code~~ ✅ (84/85 done; 1 genus has no code in source)
- **T-3b: ?FAMILY genera (29)** — uncertain family assignment; **deferred** (respecting original author intent)
- **T-3c: Chinese romanization hyphens (~30)** — possible Wade-Giles; **deferred**

### Structural Improvements

- **T-1: Expand Taxonomic Opinions** — 68 Uncertain families
  - B-1 PoC complete: `taxonomic_opinions` table + 4-trigger pattern + `is_placeholder` column
  - Agnostida Order created + SPELLING_OF opinion type added
  - Current: PLACED_IN 4 + SPELLING_OF 2 = **6 opinions**
  - **Analysis of 68 Uncertain families**: 0 families can be reassigned to another Order based on A2011. Additional literature required — **blocked**
- **T-4: Merge synonyms → taxonomic_opinions** — migrate 1,055 records as SYNONYM_OF opinions
  - Few blockers (only 1 senior_taxon_id is NULL)
  - Requires updating all queries/UI/tests referencing the synonyms table (**large scope**)

## Open Issues

- **1 unlinked synonym**: Szechuanella (syn 960) — preocc., not replaced (normal per NOTE 8)
- **325 parent_id NULL**: 257 invalid (normal) + 68 valid (FAMILY UNCERTAIN/INDET/?FAMILY etc.)
  - 29 ?FAMILY genera: uncertain family assignment, deferred (T-3b)
- **1 valid genus without temporal_code**: Dignagnostus — no code in source (T-3a complete)
- **~30 Chinese romanization hyphens**: possible Wade-Giles notation, deferred (T-3c)
- Taxa without Location/Formation are all invalid taxa (normal)

## File Structure

```
trilobase/                                 # Domain data, scripts, and tests only
├── CLAUDE.md
├── CHANGELOG.md                          # Trilobase package changelog
├── CHANGELOG_paleocore.md                # PaleoCore package changelog
├── pytest.ini                             # pytest config (testpaths=tests)
├── requirements.txt                       # scoda-engine dependency
├── db/                                    # Canonical DBs (git tracked)
│   ├── trilobase.db                       # Trilobase SQLite DB
│   └── paleocore.db                       # PaleoCore reference DB
├── dist/                                  # Build artifacts (gitignored)
│   ├── trilobase.scoda                    # .scoda package
│   ├── paleocore.scoda
│   └── *_overlay.db                       # Overlay DBs
├── data/                                  # Source data files
│   ├── trilobite_genus_list.txt           # Cleaned genus list (canonical version)
│   ├── trilobite_genus_list_original.txt
│   ├── trilobite_family_list.txt
│   ├── trilobite_nomina_nuda.txt
│   ├── adrain2011.txt
│   ├── mcp_tools_trilobase.json           # MCP tool definitions
│   └── *.pdf                              # Reference PDFs
├── spa/                                   # Reference Implementation SPA (trilobase-specific)
│   ├── index.html
│   ├── app.js
│   └── style.css
├── scripts/                               # Domain pipeline scripts
│   ├── create_scoda.py                    # trilobase.scoda → dist/
│   ├── create_paleocore_scoda.py          # paleocore.scoda → dist/
│   ├── create_paleocore.py                # PaleoCore DB → db/
│   ├── bump_version.py                    # Version bump script
│   ├── validate_manifest.py               # Manifest validator
│   ├── add_opinions_schema.py             # Taxonomic opinions migration
│   ├── add_spelling_of_opinions.py        # SPELLING_OF opinion type
│   ├── restructure_agnostida_opinions.py  # Agnostida order-level opinions
│   ├── fill_temporal_codes.py             # temporal_code auto-fill from raw_entry
│   ├── link_bibliography.py               # taxon_bibliography link builder
│   ├── create_database.py                 # DB creation → db/
│   └── ... (normalize, import, etc.)
├── tests/
│   ├── conftest.py                        # Shared fixtures
│   └── test_trilobase.py                  # Trilobase domain tests (100)
├── vendor/
│   ├── cow/v2024/States2024/statelist2024.csv
│   └── ics/gts2020/chart.ttl
├── docs/
│   ├── HANDOFF.md                         # Current status + remaining tasks (this file)
│   ├── HISTORY.md                         # Completed Phase 1~46 detailed records
│   └── paleocore_schema.md
└── devlog/

scoda-engine/                              # Separate repo: /mnt/d/projects/scoda-engine
├── pyproject.toml                         # pip install -e ".[dev]"
├── scoda_engine/                          # SCODA runtime package
│   ├── scoda_package.py, app.py, mcp_server.py, gui.py, serve.py
│   ├── templates/, static/
├── tests/                                 # Runtime tests (191)
├── scripts/                               # build.py, release.py, etc.
├── examples/, docs/
└── ScodaDesktop.spec
```

## Test Status

### Trilobase (this repo)

| File | Tests | Status |
|------|-------|--------|
| `tests/test_trilobase.py` | 100 | ✅ Passing |

### scoda-engine (separate repo)

| File | Tests | Status |
|------|-------|--------|
| `tests/test_runtime.py` | 122 | ✅ Passing |
| `tests/test_mcp.py` | 6 | ✅ 1 / ⚠ 5 (requires .scoda in CWD) |
| `tests/test_mcp_basic.py` | 1 | ✅ Passing |

**How to run:**
```bash
# Trilobase
pip install -e /mnt/d/projects/scoda-engine[dev]
pytest tests/

# scoda-engine
cd /mnt/d/projects/scoda-engine
pip install -e ".[dev]"
pytest tests/
```

**pytest config (`pytest.ini`):**
- `testpaths = tests` — test directory
- `asyncio_mode = auto` — auto-detect async tests
- `asyncio_default_fixture_loop_scope = function` — isolated event loops

## DB Schema

### Canonical DB (trilobase.db)

```sql
-- taxonomic_ranks: 5,340 records — unified taxonomy (Class~Genus) + 2 placeholders
taxonomic_ranks (
    id, name, rank, parent_id, author, year, year_suffix,
    genera_count, notes, created_at,
    -- Genus-specific fields
    type_species, type_species_author, formation, location, family,
    temporal_code, is_valid, raw_entry
)

-- synonyms: 1,055 records — synonym relationships
synonyms (id, junior_taxon_id, senior_taxon_name, senior_taxon_id,
          synonym_type, fide_author, fide_year, notes)

-- genus_formations: 4,853 records — Genus-Formation many-to-many
genus_formations (id, genus_id, formation_id, is_type_locality, notes)

-- genus_locations: 4,841 records — Genus-Country many-to-many
genus_locations (id, genus_id, country_id, region, is_type_locality, notes)

-- bibliography: 2,130 records — Literature Cited references
bibliography (id, authors, year, year_suffix, title, journal, volume, pages,
              publisher, city, editors, book_title, reference_type, raw_entry)

-- taxon_bibliography: 4,040 records — Taxon↔Bibliography FK links
taxon_bibliography (id, taxon_id, bibliography_id, relationship_type,
                    synonym_id, match_confidence, match_method, notes, created_at)

-- taxonomic_opinions: 6 records — taxonomic opinions (PLACED_IN 4 + SPELLING_OF 2)
taxonomic_opinions (id, taxon_id, opinion_type, related_taxon_id, proposed_valid,
                    bibliography_id, assertion_status, curation_confidence,
                    is_accepted, notes, created_at)
-- Triggers: trg_deactivate_before_insert, trg_sync_parent_insert,
--           trg_deactivate_before_update, trg_sync_parent_update

-- taxa: backward-compatibility view
CREATE VIEW taxa AS SELECT ... FROM taxonomic_ranks WHERE rank = 'Genus';

-- SCODA-Core tables
artifact_metadata (key, value)                    -- artifact metadata (key-value)
provenance (id, source_type, citation, description, year, url)  -- data provenance
schema_descriptions (table_name, column_name, description)      -- schema descriptions

-- SCODA UI tables
ui_display_intent (id, entity, default_view, description, source_query, priority)  -- view hints
ui_queries (id, name, description, sql, params_json, created_at)                   -- named queries
ui_manifest (name, description, manifest_json, created_at)                         -- declarative view defs (JSON)

-- Note: 8 PaleoCore tables were DROPped in Phase 34
-- countries, formations, geographic_regions, cow_states, country_cow_mapping,
-- temporal_ranges, ics_chronostrat, temporal_ics_mapping → paleocore.db (pc.* prefix)
```

### Overlay DB (trilobase_overlay.db)

```sql
-- overlay_metadata: canonical DB version tracking
overlay_metadata (key, value)  -- canonical_version, created_at

-- user_annotations: user annotations
user_annotations (
    id, entity_type, entity_id, entity_name,  -- entity_name: cross-release matching
    annotation_type, content, author, created_at
)
```

**SQLite ATTACH usage (3-DB):**
```python
conn = sqlite3.connect('db/trilobase.db')  # Canonical DB
conn.execute("ATTACH DATABASE 'dist/trilobase_overlay.db' AS overlay")
conn.execute("ATTACH DATABASE 'db/paleocore.db' AS pc")

# Canonical tables: SELECT * FROM taxonomic_ranks
# Overlay tables:   SELECT * FROM overlay.user_annotations
# PaleoCore tables: SELECT * FROM pc.countries
# Cross-DB JOIN:    SELECT ... FROM genus_locations gl JOIN pc.countries c ON gl.country_id = c.id
```

## DB Usage Examples

```bash
# Basic query (using taxa view)
sqlite3 db/trilobase.db "SELECT * FROM taxa LIMIT 10;"

# Full hierarchy query
sqlite3 db/trilobase.db "SELECT g.name, f.name as family, o.name as 'order'
FROM taxonomic_ranks g
LEFT JOIN taxonomic_ranks f ON g.parent_id = f.id
LEFT JOIN taxonomic_ranks sf ON f.parent_id = sf.id
LEFT JOIN taxonomic_ranks o ON sf.parent_id = o.id
WHERE g.rank = 'Genus' AND g.is_valid = 1 LIMIT 10;"

# Genus formations (using relation table)
sqlite3 db/trilobase.db "SELECT g.name, f.name as formation
FROM taxonomic_ranks g
JOIN genus_formations gf ON g.id = gf.genus_id
JOIN formations f ON gf.formation_id = f.id
WHERE g.name = 'Paradoxides';"

# Genera by country (using relation table)
sqlite3 db/trilobase.db "SELECT g.name, gl.region
FROM taxonomic_ranks g
JOIN genus_locations gl ON g.id = gl.genus_id
JOIN countries c ON gl.country_id = c.id
WHERE c.name = 'China' LIMIT 10;"
```

## Notes

- `data/trilobite_genus_list.txt` is always the canonical text version
- `db/trilobase.db` is the latest database
- Git commit after each Phase completion
- Original PDF reference: Jell & Adrain (2002)
