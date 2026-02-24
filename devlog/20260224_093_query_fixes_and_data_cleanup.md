# 093: ui_queries pc.* prefix 수정 및 genus_locations 데이터 정합성 복원

**Date:** 2026-02-24

## 문제

Phase 34에서 PaleoCore 테이블을 `paleocore.db`로 분리하면서 `pc.*` prefix가 필요해졌으나, 여러 ui_queries가 업데이트되지 않음.

### 발견된 이슈

1. **formations_list, countries_list**: `taxa_count` 컬럼이 PaleoCore 테이블에 존재하지 않음
2. **regions_list**: paleocore DB 내부 쿼리라 `pc.` prefix 없이 작성됐으나, trilobase 컨텍스트에서 실행 시 실패
3. **genus_formations**: `JOIN formations f` → `pc.formations` 필요
4. **genera_by_country**: `JOIN countries c` → `pc.geographic_regions` 필요
5. **genus_locations**: 컬럼명(country, region)이 매니페스트 기대값(country_name, region_name)과 불일치
6. **genus_locations.country_id 데이터 오류**: 4,841건 중 3,750건(77%)에서 country_id가 region_id의 부모 country와 불일치

## 수정 사항

### ui_queries 수정 (`add_scoda_ui_tables.py`)

| 쿼리 | 변경 |
|------|------|
| `formations_list` | `pc.formations` + COUNT 서브쿼리로 taxa_count 계산 |
| `countries_list` | `pc.geographic_regions` + COUNT 서브쿼리로 taxa_count 계산 |
| `regions_list` | trilobase에 새로 추가, `pc.geographic_regions` + COUNT 서브쿼리 |
| `genus_formations` | `JOIN formations` → `JOIN pc.formations` |
| `genera_by_country` | `JOIN countries` → `JOIN pc.geographic_regions` |
| `genus_locations` | region_id → parent_id 계층에서 country 파생, 컬럼명 매니페스트와 일치 |
| `rank_children` | LIMIT 20 제거 |

### genus_locations 데이터 수정

```sql
UPDATE genus_locations
SET country_id = (SELECT parent_id FROM pc.geographic_regions WHERE id = genus_locations.region_id)
WHERE region_id IS NOT NULL
  AND country_id <> (SELECT parent_id FROM pc.geographic_regions WHERE id = genus_locations.region_id);
-- 3,750 rows updated
```

수정 후 불일치: 0건

## 변경된 파일

| 파일 | 변경 |
|------|------|
| `scripts/add_scoda_ui_tables.py` | 7개 쿼리 수정/추가 |
| `db/trilobase.db` | 쿼리 반영 + genus_locations country_id 3,750건 수정 |
| `CHANGELOG.md` | 0.2.3 항목 추가 |

## 테스트

- trilobase: 101 tests passing
