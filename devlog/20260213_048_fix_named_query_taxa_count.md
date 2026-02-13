# Fix: ui_queries의 taxa_count 컬럼 참조 오류

**날짜:** 2026-02-13
**유형:** Bugfix

## 증상

- Web UI에서 Countries 탭, Formations 탭 클릭 시 "Error loading data" 표시
- Flask 서버 로그에는 아무 에러도 찍히지 않음

## 원인

`ui_queries` 테이블에 저장된 두 named query가 `taxa_count` 컬럼을 직접 참조:

- `countries_list`: `SELECT id, name, cow_ccode as code, taxa_count FROM pc.geographic_regions ...`
- `formations_list`: `SELECT id, name, formation_type, country, period, taxa_count FROM pc.formations ...`

Phase 31에서 paleocore.db 생성 시 `taxa_count` 컬럼을 제거했으나, `ui_queries`의 SQL은 업데이트하지 않음.

Phase 47 bugfix(2026-02-13)에서 `app.py`의 detail API 3개(`/api/country/<id>`, `/api/region/<id>`, `/api/formation/<id>`)는 수정했지만, **named query SQL은 누락**.

### Flask 로그가 없었던 이유

`api_query_execute()`가 SQL 에러를 `except`로 잡아 HTTP 400 JSON 응답으로 반환 → Flask는 정상 응답으로 처리 → 에러 로그 미출력. 프론트엔드는 `!response.ok`만 체크하여 "Error loading data" 표시.

## 수정

`trilobase.db`의 `ui_queries` 테이블에서 두 쿼리의 SQL을 `JOIN + COUNT(DISTINCT)`로 업데이트:

### countries_list

```sql
SELECT gr.id, gr.name, gr.cow_ccode as code,
       COUNT(DISTINCT gl.genus_id) as taxa_count
FROM pc.geographic_regions gr
LEFT JOIN genus_locations gl ON gl.region_id = gr.id
    OR gl.region_id IN (SELECT id FROM pc.geographic_regions WHERE parent_id = gr.id)
WHERE gr.level = 'country'
GROUP BY gr.id
ORDER BY gr.name
```

### formations_list

```sql
SELECT f.id, f.name, f.formation_type, f.country, f.period,
       COUNT(DISTINCT gf.genus_id) as taxa_count
FROM pc.formations f
LEFT JOIN genus_formations gf ON gf.formation_id = f.id
GROUP BY f.id
ORDER BY f.name
```

## 검증

- countries_list: 60행 반환 확인
- formations_list: 2,004행 반환 확인
- test_app.py: 161개 전부 통과
