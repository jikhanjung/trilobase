# P78: Treatise (2004) Taxonomy Import Plan

**Date:** 2026-03-01
**Type:** Plan
**Status:** Implemented

## Goal

Import Treatise on Invertebrate Paleontology (2004) Agnostida (ch4) and Redlichiida (ch5) classification into the assertion-centric DB as a third taxonomic opinion source.

## Key Decisions

- **Eodiscida**: Reuse existing taxon (id=2), place under Agnostida via Treatise assertion
- **Subgenus**: Skip in this phase, genus-level only
- **3 new genera**: Iofgia, Macannaia, Pseudopaokannia added to taxon table
- **Agnostida**: Placed within Trilobita in Treatise profile
- **Edge cache**: Hybrid approach — default edges + Treatise overrides for covered taxa

## Implementation

1. `scripts/import_treatise.py` — incremental import after `create_assertion_db.py`
2. `scripts/validate_treatise_import.py` — 17-check validation
3. `scripts/create_assertion_db.py` — Subfamily rank_radius in radial tree
4. `scripts/validate_assertion_db.py` — relaxed counts for post-import state

## Execution Order

```bash
python scripts/create_assertion_db.py
python scripts/import_treatise.py
python scripts/validate_treatise_import.py
python scripts/validate_assertion_db.py
```
