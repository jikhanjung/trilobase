# P54: Generic Viewer Auto-Discovery (detail view 자동 생성)

## 배경

현재 generic viewer는 manifest에 table view + detail view가 모두 정의되어야 목록 → 클릭 → 디테일 흐름이 동작한다. paleocore의 `temporal_ranges_table`처럼 table view는 있지만 detail view가 빠져있으면 클릭해도 아무 일도 안 일어남.

**목표**: manifest에 table view가 정의된 테이블은, detail view가 명시적으로 없더라도 ScodaDesktop이 자동으로 detail을 보여줄 수 있게 한다.

## 설계 원칙

- **탭 (어떤 테이블을 보여줄지)**: 항상 manifest가 결정 → 패키지 제작자의 몫
- **list 내용**: manifest의 table view 정의 사용 (columns, sort, search 등)
- **detail 내용**: manifest에 detail view가 있으면 사용, **없으면 DB 스키마에서 자동 생성**

## 현재 데이터 흐름

```
탭 클릭 (table view)
  → manifest.views[viewKey].on_row_click.detail_view 확인
  → 있으면 openDetail(detail_view, id) → 모달 표시
  → 없으면 클릭 불가 (on_row_click 자체가 없음)

행 클릭 (detail view)
  → view.source 있으면 → fetch(view.source)      → /api/detail/{query}
  → view.source 없으면 → fetch(/api/composite/)   → source_query + sub_queries
```

## 수정 범위

### 1. `app.py` — `/api/auto/detail/{table_name}` 엔드포인트 추가

manifest에 detail view가 없는 테이블을 위한 자동 detail 엔드포인트.

```
GET /api/auto/detail/{table_name}?id=N

1. sqlite_master에서 table_name 존재 확인 (SQL injection 방지)
2. PRAGMA table_info()로 PK 컬럼 찾기
3. SELECT * FROM [table] WHERE [pk] = ? 실행
4. 첫 행 반환 (flat JSON)
```

### 2. `app.js` — `openDetail()` fallback 로직 추가

manifest에 detail view가 없을 때, 자동으로 detail을 표시하는 로직.

```javascript
async function openDetail(viewKey, entityId) {
    if (manifest && manifest.views[viewKey]) {
        // 기존: manifest에 detail view가 있으면 사용
        await renderDetailFromManifest(viewKey, entityId);
    } else if (viewKey.endsWith('_detail')) {
        // 신규: detail view가 없으면 auto detail 사용
        const table = viewKey.replace('_detail', '');
        await renderAutoDetail(table, entityId);
    }
}
```

`renderAutoDetail(table, entityId)`:
1. `GET /api/auto/detail/{table}?id={entityId}` 호출
2. 응답의 모든 키를 `field_grid`로 렌더링 (label = key의 Title Case)
3. 모달 제목 = `data.name || data.code || data.id`

### 3. `app.js` — table view 행 클릭 fallback

manifest의 table view에 `on_row_click`이 없을 때, PK 기반으로 자동 클릭 활성화.

```javascript
// renderTableView() 또는 renderTableViewRows() 에서:
const rowClick = view.on_row_click;
const autoClick = !rowClick && view._auto_table;  // auto에서 왔는지
// auto인 경우 → openDetail('{table}_detail', row.id) 자동 연결
```

→ 이건 구현 복잡도 대비 효과가 적으므로, **manifest에 on_row_click을 넣어주는 걸 기본으로** 하고, 이 fallback은 나중에 필요할 때 추가.

## 구현 순서

1. `/api/auto/detail/{table_name}` 엔드포인트 추가 (app.py)
2. `renderAutoDetail()` 함수 추가 (app.js)
3. `openDetail()` fallback 로직 추가 (app.js)
4. 테스트 추가

## 보안 고려

| 위협 | 대응 |
|------|------|
| SQL injection (테이블명) | `sqlite_master`에서 존재 확인 후에만 쿼리 실행 |
| 테이블명 escape | `[{table_name}]` bracket quoting |
| 메타데이터 테이블 접근 | SCODA 메타데이터 테이블 접근 차단 (선택) |

## 검증 계획

1. `pytest tests/ -x -q` — 기존 217개 테스트 통과
2. 새 테스트 추가:
   - `/api/auto/detail/{table}?id=N` → 정상 응답
   - 존재하지 않는 테이블 → 404
   - 존재하지 않는 id → 404
3. 수동 테스트: manifest에 detail view 없는 table view에서 행 클릭 → auto detail 모달 표시
