# P78: Treatise (2004) Taxonomy Import

**Date:** 2026-03-01
**Type:** Implementation
**Phase:** P78

## Summary

Imported Treatise on Invertebrate Paleontology (2004) Agnostida and Redlichiida
classification as a third taxonomic opinion source into the assertion-centric DB.

## Results

| Metric | Count |
|--------|-------|
| References added | 2 (Shergold et al. ch4, Palmer & Repina ch5) |
| Taxa matched | 370 |
| Taxa created | 50 |
| PLACED_IN assertions | 421 |
| treatise2004 profile edges | 5,138 (vs default 5,083) |

### New Taxa Breakdown

| Rank | Count | Examples |
|------|-------|---------|
| Superfamily | 3 | AGNOSTOIDEA, CONDYLOPYGOIDEA, EODISCOIDEA |
| Family | 4 | SPINAGNOSTIDAE, PHALACROMIDAE, SPHAERAGNOSTIDAE, Menneraspidae |
| Subfamily | 32 | AGNOSTINAE, AMMAGNOSTINAE, Olenellinae, etc. |
| Genus | 3 | Iofgia, Macannaia, Pseudopaokannia |
| Placeholder | 8 | uncertain containers (ch4/ch5), Unrecognizable container |

### Assertion Status Distribution

| Status | Count | Description |
|--------|-------|-------------|
| asserted | 367 | Normal placement |
| questionable | 17 | Genera with `uncertain: true` flag |
| incertae_sedis | 27 | Taxa under "uncertain" containers |
| indet | 10 | Unrecognizable redlichioid genera |

## Key Design Decisions

1. **Eodiscida reuse**: Existing Eodiscida (id=2) placed under Agnostida via Treatise
   assertion. Notes field records "Treatise (2004): Suborder Eodiscina of Agnostida".

2. **Hybrid edge cache**: Start with all default edges, replace only taxa that the
   Treatise explicitly places. Genera not mentioned in the Treatise keep their
   default placement. Result: all 4,860 default genera preserved + 7 new.

3. **is_accepted=0**: All Treatise assertions are non-accepted (alternative opinion).
   Default profile unchanged.

4. **Subfamily rank**: New rank type added. 32 subfamilies created. Radial tree
   rank_radius updated to accommodate 7 rank levels.

## Files Changed

| File | Action | Description |
|------|--------|-------------|
| `scripts/import_treatise.py` | New | ~350 lines, incremental import |
| `scripts/validate_treatise_import.py` | New | ~200 lines, 17 checks |
| `scripts/create_assertion_db.py` | Modified | Subfamily in rank_radius + schema_descriptions |
| `scripts/validate_assertion_db.py` | Modified | Relaxed counts for post-import state |

## Validation

- `validate_treatise_import.py`: 17/17 checks passed
- `validate_assertion_db.py`: 15/15 checks passed
- `pytest tests/`: 112/112 tests passed
