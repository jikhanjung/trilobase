# devlog 099 — Modular Rebuild Pipeline 완성 (35/35 검증 통과)

**Date:** 2026-02-28
**Phase:** P72 Implementation (rebuild pipeline)

## Summary

P72에서 설계한 **모듈화된 빌드 파이프라인**을 완전히 구현하여 소스 텍스트 2개로부터
현재 DB와 동일한 결과를 한 번에 생성. **35/35 검증 항목 전수 통과**, 112개 테스트 통과.

## Pipeline Structure

```
scripts/
  pipeline/
    __init__.py           # 패키지 init
    clean.py              # Step 1: text loading
    hierarchy.py          # Step 2: adrain2011 + family hierarchy
    parse_genera.py       # Step 3: genus entry parsing (개선판)
    load_data.py          # Step 4: schema + data load
    paleocore.py          # Step 5: PaleoCore DB 생성
    junctions.py          # Step 6: genus_formations, genus_locations
    metadata.py           # Step 7: SCODA metadata + UI
    validate.py           # Step 8: validation (35 checks)
  rebuild_database.py     # orchestrator
```

**실행:**
```bash
python scripts/rebuild_database.py --output-dir dist/rebuild/ --validate
```

**출력:** `dist/rebuild/trilobase.db` + `dist/rebuild/paleocore.db`

## Validation Results (35/35)

| Category | Check | Result |
|----------|-------|--------|
| Trilobase | taxonomic_ranks total | 5,341 ✓ |
| | Class/Order/Suborder/Superfamily/Family | 1/13/9/13/190 ✓ |
| | Genus count | 5,115 ✓ |
| | valid/invalid genera | 4,259/856 ✓ |
| | parent_id NULL (valid) | 0 ✓ |
| | opinions total | 1,139 ✓ |
| | SYNONYM_OF | 1,055 ✓ |
| | PLACED_IN | 82 ✓ |
| | SPELLING_OF | 2 ✓ |
| | bibliography | 2,131 ✓ |
| | taxon_bibliography | 4,236 (≥4,100) ✓ |
| | genus_formations | 4,550 (≥4,500) ✓ |
| | genus_locations | 4,853 (≥4,840) ✓ |
| | temporal_ranges | 28 ✓ |
| | SCODA metadata (5 tables) | all ✓ |
| Quality | no formation=country | 0 ✓ |
| | no China→England swap | 0 ✓ |
| PaleoCore | countries | 142 ✓ |
| | formations | 1,814 (≥1,800) ✓ |
| | geographic_regions | 685 (≥600) ✓ |
| | cow_states | 244 ✓ |
| | ics_chronostrat | 178 ✓ |
| | temporal_ics_mapping | 40 ✓ |

## Key Improvements over Original Pipeline

### 1. is_valid 판정 (4,259/856 exact match)
- s.o.s. (senior objective synonym) = VALID (원래 잘못 invalidated)
- `\bsuppressed\b` anywhere matching (mid-bracket 'suppressed in favour of' 포착)
- NOTE 8 second-occurrence handling (junior homonym만 invalid)
- Compound invalidity: replacement name + preocc./j.o.s.
- 2 edge-case overrides: Deucalion(valid), Nitidocare(invalid)

### 2. Formation/Location 분리 (Type 3 reclassification)
- 308 entries: formation→region reclassification
- "Sandby, Sweden" → formation=None, region="Sandby", country="Sweden"
- Region granularity: first sub-region part only (matching reference)

### 3. PLACED_IN opinions (82 exact match)
- 22 suborder-uncertain (AGNOSTINA/REDLICHIINA/OLENELLINA)
- 43 questionable (?FAMILY/??FAMILY)
- 17 manual curations (14 indet + 2 Eurekiidae PoC + 1 Costapyge)

### 4. Synonym→Opinion pipeline
- _clean_senior_name(): "Platynotus CONRAD, 1838" → "Platynotus"
- suppressed pattern: capture "in favour of X" name
- Dedup: skip preocc.(NULL) when j.s.s.(name) exists for same genus

### 5. Bibliography parsing
- Year-only line detection: dot optional (`1960 (ed.)` now matched)
- 5 previously missed entries recovered

### 6. Hierarchy parsing
- Footnote digit stripping: "Uncertain37" → "Uncertain" (attached digits)
- Correctly creates "Uncertain" Order node for Eurekiidae opinions

### 7. Family parsing fallbacks
- 6 fallback regexes for non-standard formatting
- FAMILY_OVERRIDES for unparseable entries (Melopetasus)

## Debug Journey (27/35 → 35/35)

| Round | Pass | Key Fixes |
|-------|------|-----------|
| 1 | 27/35 | Initial build |
| 2 | 27/35 | is_valid patterns, PLACED_IN for suborder uncertain |
| 3 | 27/35 | s.o.s. is VALID, suppressed anywhere, NOTE 8 post-process |
| 4 | 29/35 | valid/invalid exact; family fallback regexes |
| 5 | 30/35 | parent_id NULL → 0; _clean_senior_name |
| 6 | 31/35 | Synonym dedup (preocc.+j.s.s.) |
| 7 | 35/35 | Bibliography dot, hierarchy footnotes, manual PLACED_IN, Type 3 |

## Files Created/Modified

### New Files (pipeline/)
- `scripts/pipeline/__init__.py`
- `scripts/pipeline/clean.py` (~30 lines)
- `scripts/pipeline/hierarchy.py` (~297 lines)
- `scripts/pipeline/parse_genera.py` (~638 lines)
- `scripts/pipeline/load_data.py` (~1,220 lines)
- `scripts/pipeline/paleocore.py` (~940 lines)
- `scripts/pipeline/junctions.py` (~180 lines)
- `scripts/pipeline/metadata.py` (~60 lines)
- `scripts/pipeline/validate.py` (~150 lines)
- `scripts/rebuild_database.py` (~80 lines)

### Unchanged
- `db/trilobase.db`, `db/paleocore.db` — not touched
- All existing `scripts/*.py` — not modified
