# Formation Detail 링크 추가 (Country, Period→ICS)

**날짜:** 2026-02-15

## 목표

Formation detail 모달에서 country, period가 plain text로 표시되던 것을 클릭 가능한 링크로 변경.

## 변경 사항

### 1. `formation_detail` SQL 쿼리 수정 (`trilobase.db`)

기존 SQL에 두 개의 LEFT JOIN 추가:

```sql
LEFT JOIN pc.geographic_regions gr ON f.country = gr.name AND gr.level = 'country'
LEFT JOIN pc.temporal_ranges tr ON f.period = tr.name
```

- `country_id`: geographic_regions.id 반환 (country_detail 링크용)
- `temporal_code`: temporal_ranges.code 반환 (ICS 매핑용)

### 2. `formation_detail` manifest 수정

| 필드 | 변경 전 | 변경 후 |
|------|---------|---------|
| country | plain text | `format: "link"`, `link: {detail_view: "country_detail", id_path: "country_id"}` |
| period | plain text | `format: "temporal_range"` → `buildTemporalRangeHTML()` 재사용 |

`sub_queries`에 `temporal_ics_mapping` 추가 (기존 `genus_ics_mapping` named query 재사용):

```json
"temporal_ics_mapping": {
    "query": "genus_ics_mapping",
    "params": {"temporal_code": "result.temporal_code"}
}
```

### 3. 테스트 데이터 보강 (`tests/conftest.py`)

- `formation_detail` SQL/manifest 동기화
- `temporal_ranges`에 `DEV`(Devonian), `CAM`(Cambrian) 추가 — formation period 매칭용
- `temporal_ics_mapping`에 `DEV → Paleozoic(partial)` 매핑 추가

## SPA 변경 없음

- `format: "link"` → 기존 `formatFieldValue` case 'link' 처리
- `format: "temporal_range"` → 기존 `buildTemporalRangeHTML()` 처리
- 백엔드(DB 쿼리 + manifest)만 변경하여 구현 완료

## 변경 파일

| 파일 | 변경 |
|------|------|
| `trilobase.db` | `ui_queries.formation_detail` SQL, `ui_manifest` JSON |
| `tests/conftest.py` | SQL, manifest, temporal_ranges/temporal_ics_mapping 데이터 추가 |
| `tests/test_trilobase.py` | `test_mapping_table_exists` count 5→6 |

## 테스트

```
pytest tests/ -x -q
226 passed
```
