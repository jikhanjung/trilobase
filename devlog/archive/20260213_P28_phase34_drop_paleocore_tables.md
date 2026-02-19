# Plan: Phase 34 — trilobase.db에서 PaleoCore 테이블 DROP

**날짜:** 2026-02-13
**상태:** 계획

## 배경

Phase 33에서 모든 앱 쿼리를 `pc.*` prefix로 전환 완료. trilobase.db에 남아있는 PaleoCore 테이블 8개는 이제 중복이므로 DROP하여 DB를 정리한다.

## DROP 대상 테이블 (8개)

| 테이블 | trilobase.db 레코드 | paleocore.db 존재 |
|---|---|---|
| countries | 142 | ✅ |
| geographic_regions | 562 | ✅ |
| formations | 2,006 | ✅ |
| cow_states | 244 | ✅ |
| country_cow_mapping | 142 | ✅ |
| temporal_ranges | 28 | ✅ |
| ics_chronostrat | 178 | ✅ |
| temporal_ics_mapping | 40 | ✅ |

## 수정 작업

### 1. trilobase.db — DROP TABLE 8개

```sql
DROP TABLE IF EXISTS country_cow_mapping;
DROP TABLE IF EXISTS cow_states;
DROP TABLE IF EXISTS temporal_ics_mapping;
DROP TABLE IF EXISTS ics_chronostrat;
DROP TABLE IF EXISTS geographic_regions;
DROP TABLE IF EXISTS formations;
DROP TABLE IF EXISTS countries;
DROP TABLE IF EXISTS temporal_ranges;
```

FK 의존 테이블 먼저 DROP (country_cow_mapping → countries 등).

### 2. trilobase.db — ui_queries SQL 업데이트 (6개)

| name | 현재 | → 변경 |
|---|---|---|
| `countries_list` | `FROM geographic_regions` | `FROM pc.geographic_regions` |
| `formations_list` | `FROM formations` | `FROM pc.formations` |
| `genera_by_country` | `JOIN countries c` | `JOIN pc.countries c` |
| `genus_formations` | `JOIN formations f` | `JOIN pc.formations f` |
| `genus_locations` | `JOIN countries c` | `JOIN pc.countries c` |
| `regions_list` | `geographic_regions` (2곳) | `pc.geographic_regions` (2곳) |

### 3. trilobase.db — schema_descriptions 정리

DROP된 8개 테이블의 schema_descriptions 행 삭제.

### 4. test_app.py — canonical test DB에서 PaleoCore 테이블 제거

- CREATE TABLE + INSERT 제거: countries, formations, geographic_regions, ics_chronostrat, temporal_ics_mapping
- genus_locations FK 정의에서 `FOREIGN KEY (country_id) REFERENCES countries(id)` 제거
- genus_formations FK 정의에서 `FOREIGN KEY (formation_id) REFERENCES formations(id)` 제거

### 5. test_app.py — TestICSChronostrat 9개 테스트 수정

현재: `canonical_db, _, _ = test_db` → `sqlite3.connect(canonical_db)`
변경: `_, _, paleocore_db = test_db` → `sqlite3.connect(paleocore_db)`

### 6. scripts/release.py — formations/countries 통계 제거

- `get_statistics()`: `FROM formations`, `FROM countries` COUNT 쿼리 삭제
- `generate_readme()`: formations/countries 통계 출력 제거
- `test_app.py` → `TestRelease.test_get_statistics`, `test_generate_readme` 어서션 업데이트

## 수정 파일

- `trilobase.db` — DROP 8개 + ui_queries 6개 + schema_descriptions 정리
- `test_app.py` — fixture 정리 + TestICSChronostrat + TestRelease
- `scripts/release.py` — formations/countries 통계 제거

## 검증

```bash
pytest test_app.py -v    # 147개
pytest test_mcp.py -v    # 17개
```
