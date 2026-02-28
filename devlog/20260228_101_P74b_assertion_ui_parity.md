# P74b — Assertion DB UI 기능 동등화 + Classification Profile 표시

**Date:** 2026-02-28
**Phase:** P74b

## 개요

P74에서 생성한 assertion-centric test DB에 기존 trilobase UI와 동등한 기능을 추가.
Junction table, PaleoCore 의존성, geography/formation/bibliography UI, classification profile 표시 구현.

## 변경 파일

| 파일 | 변경 |
|------|------|
| `scripts/create_assertion_db.py` | junction table 복사 + UI queries 40개 + manifest 15 views |
| `scripts/create_assertion_scoda.py` | paleocore 의존성 추가 |
| `scripts/validate_assertion_db.py` | junction table 건수 검증 3개 추가 |

## 주요 변경사항

### 1. 네이밍 일관성: `taxon_bibliography` → `taxon_reference`

assertion DB에서 `bibliography` → `reference`로 테이블명을 변경했으므로,
junction table도 일관되게:
- 테이블명: `taxon_bibliography` → `taxon_reference`
- 컬럼명: `bibliography_id` → `reference_id`

### 2. Junction table 복사 (3개)

canonical DB(`db/trilobase.db`)에서 assertion DB로 데이터 복사:

| 테이블 | 건수 |
|--------|------|
| `genus_formations` | 4,503 |
| `genus_locations` | 4,849 |
| `taxon_reference` | 4,173 |

### 3. UI Queries 확장: 13개 → 40개

신규 쿼리 (~27개):
- **Genus-specific:** `genus_hierarchy`, `genus_ics_mapping`, `genus_formations`, `genus_locations`, `genus_bibliography`, `taxon_bibliography`
- **Formations (pc.*):** `formations_list`, `formation_detail`, `formation_genera`
- **Countries/Regions (pc.*):** `countries_list`, `country_detail`, `country_regions`, `country_genera`, `regions_list`, `region_detail`, `region_genera`
- **ICS Chronostratigraphy (pc.*):** `ics_chronostrat_list`, `chronostrat_detail`, `chronostrat_children`, `chronostrat_mappings`, `chronostrat_genera`
- **Cross-cutting:** `genera_by_country`, `genera_by_period`, `valid_genera_list`
- **Profiles:** `profile_detail`, `profile_edges`
- **Reference:** `reference_genera`

주요 adaptation:
- `taxonomic_ranks` → `taxon`
- `bibliography` → `reference`
- `parent_id` 직접 참조 → assertion JOIN 또는 `v_taxonomic_ranks.parent_id`
- `pc.*` 테이블 참조는 동일 유지

### 4. UI Manifest 확장: 6 views → 15 views

**Tab views (8):**
1. `taxonomy_tree` — 프로필 표시 추가
2. `genera_table`
3. `assertion_table`
4. `reference_table`
5. `formations_table` — **신규**
6. `countries_table` — **신규**
7. `chronostratigraphy_table` — **신규** (nested_table ICS chart)
8. `profiles_table` — **신규** (classification profiles 목록)

**Detail views (7):**
9. `taxon_detail_view` — Genus rank → `genus_detail`로 redirect
10. `genus_detail` — **신규** (hierarchy, locations, formations, bibliography, synonymy, assertions)
11. `reference_detail_view` — genera 링크 추가
12. `formation_detail` — **신규**
13. `country_detail` — **신규** (regions + genera)
14. `region_detail` — **신규**
15. `chronostrat_detail` — **신규** (children, mappings, genera)
16. `profile_detail_view` — **신규** (edge 통계, rule JSON)

### 5. PaleoCore 의존성

`.scoda` 패키지 manifest에 paleocore 의존성 추가:
```json
{
    "name": "paleocore",
    "alias": "pc",
    "version": ">=0.1.1,<0.2.0",
    "file": "paleocore.scoda",
    "required": true
}
```

### 6. Classification Profile 표시

- `profiles_table`: 프로필 목록 (name, description, edge count)
- `profile_detail_view`: 프로필 상세 (rule JSON, Order/Family/Genus 수, edge 목록)
- `taxonomy_tree` description에 현재 프로필 표시

## 검증 결과

```
validate_assertion_db.py — 15/15 checks passed
create_assertion_scoda.py — 1.3MB, checksum OK, paleocore dependency OK
```

### DB 통계

| 항목 | 값 |
|------|-----|
| taxon | 5,341 |
| reference | 2,132 |
| assertion | 6,142 |
| genus_formations | 4,503 |
| genus_locations | 4,849 |
| taxon_reference | 4,173 |
| classification_edge_cache | 5,083 |
| ui_queries | 40 |
| manifest views | 15 |
