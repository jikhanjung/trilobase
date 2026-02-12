# Phase 34: trilobase.db에서 PaleoCore 테이블 DROP

**날짜:** 2026-02-13
**상태:** ✅ 완료

## 작업 내용

Phase 33에서 모든 앱 쿼리를 `pc.*` prefix로 전환 완료했으므로, trilobase.db에 남아있던 PaleoCore 중복 테이블 8개를 DROP하여 DB를 정리.

### 1. trilobase.db — DROP TABLE 8개

FK 의존 순서로 DROP:

| 테이블 | DROP된 레코드 |
|---|---|
| country_cow_mapping | 142 |
| cow_states | 244 |
| temporal_ics_mapping | 40 |
| ics_chronostrat | 178 |
| geographic_regions | 562 |
| formations | 2,004 |
| countries | 142 |
| temporal_ranges | 28 |
| **합계** | **3,340** |

### 2. trilobase.db — ui_queries SQL 업데이트 (6개)

| id | name | 변경 내용 |
|---|---|---|
| 8 | genus_formations | `JOIN formations f` → `JOIN pc.formations f` |
| 9 | genus_locations | `JOIN countries c` → `JOIN pc.countries c` |
| 11 | formations_list | `FROM formations` → `FROM pc.formations` |
| 12 | countries_list | `FROM geographic_regions` → `FROM pc.geographic_regions` |
| 13 | genera_by_country | `JOIN countries c` → `JOIN pc.countries c` |
| 15 | regions_list | `geographic_regions` → `pc.geographic_regions` (2곳) |

### 3. trilobase.db — schema_descriptions 정리

DROP된 테이블의 schema_descriptions 행 삭제 (49행):

| 테이블 | 삭제 행 |
|---|---|
| countries | 5 |
| formations | 9 |
| geographic_regions | 7 |
| temporal_ranges | 8 |
| ics_chronostrat | 14 |
| temporal_ics_mapping | 6 |
| cow_states | 0 (없음) |
| country_cow_mapping | 0 (없음) |

schema_descriptions: 143 → 94행

### 4. test_app.py 수정

- **canonical test DB fixture**: countries, formations, geographic_regions, ics_chronostrat, temporal_ics_mapping의 CREATE TABLE + INSERT 제거
- **genus_locations/genus_formations FK**: countries/formations 참조 FK 제거
- **TestICSChronostrat 9개 테스트**: `canonical_db` → `paleocore_db` 전환
- **TestRelease.test_get_statistics**: formations/countries 어서션 제거
- **TestApiMetadata**: formations/countries 통계 어서션 제거

### 5. scripts/release.py 수정

- `get_statistics()`: formations/countries COUNT 쿼리 제거
- `generate_readme()`: Formations/Countries 통계 출력 행 제거

## 수정 파일

| 파일 | 변경 |
|---|---|
| `trilobase.db` | DROP 8개 + ui_queries 6개 + schema_descriptions 49행 삭제 |
| `test_app.py` | fixture 정리 + TestICSChronostrat + TestRelease + TestApiMetadata |
| `scripts/release.py` | formations/countries 통계 제거 |

## 테스트 결과

```
pytest test_app.py -v      # 147 passed
pytest test_mcp.py -v       # 16 passed
pytest test_mcp_basic.py -v # 1 passed
합계: 164 passed
```

## DB 현황 (변경 후)

trilobase.db 잔여 테이블 (13개 + 1 view):
- taxonomic_ranks, synonyms, genus_formations, genus_locations, bibliography
- artifact_metadata, provenance, schema_descriptions
- ui_display_intent, ui_queries, ui_manifest
- user_annotations, sqlite_sequence
- taxa (view)
