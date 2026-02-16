# 069: Generic Viewer 도메인 독립화 + Detail View 링크

## 작업 내용

ScodaDesktop의 generic viewer를 완전히 도메인-독립적(domain-agnostic)으로 리팩터링.
trilobase 전용 코드를 제거하고, 모든 동작을 manifest-driven으로 전환.

## 주요 변경

### 1. Generic Viewer 도메인 독립화 (`scoda_desktop/`)

**하드코딩 제거:**
- `'rank_detail'`, `'chronostrat_detail'` 등 view 이름 기본값 제거
- `taxonomy_tree`, `family_genera` 등 쿼리 이름 예시 제거
- `temporal_code`, `ics_mapping` 등 필드명 하드코딩 제거
- "Trilobase" 문자열 → "SCODA Desktop"으로 변경

**영향 파일:**
- `static/js/app.js` — buildHierarchyHTML, buildTemporalRangeHTML, tree/chart 렌더러
- `static/css/style.css` — 주석
- `serve.py` — docstring, 종료 메시지
- `scoda_package.py` — 예시 파일명
- `mcp_server.py` — 도구 설명 예시
- `app.py` — 주석

### 2. Manifest-Driven 링크 시스템

`buildHierarchyHTML(field, data)`, `buildTemporalRangeHTML(field, data)`가 manifest field 정의에서 링크 대상을 읽도록 변경:

```json
{
  "key": "hierarchy", "format": "hierarchy",
  "data_key": "hierarchy",
  "link": {"detail_view": "rank_detail"}
}
```
```json
{
  "key": "temporal_code", "format": "temporal_range",
  "mapping_key": "ics_mapping",
  "link": {"detail_view": "chronostrat_detail"}
}
```

Tree `on_node_info`, Chart `cell_click`도 manifest에 `detail_view`가 있을 때만 동작.

### 3. Entity Detail API 엔드포인트

`GET /api/{entity_name}/{entity_id}` — manifest `source` URL 패턴 처리:
- `{entity}_detail` named query 실행
- `{entity}_*` sub-query 자동 발견 및 실행
- composite JSON 반환 (hierarchy, ics_mapping 등 포함)
- catch-all 패턴이므로 기존 라우트 뒤에 등록

### 4. Auto-Discovery Manifest 생성 (`app.py`)

`_auto_generate_manifest()`: ui_manifest 테이블이 없는 DB에 대해 스키마 기반 manifest 자동 생성.
- 각 테이블 → table view + detail view
- `_fetch_manifest()` fallback chain: ui_manifest → auto-generate

### 5. SPA Extract 기능 제거 (`gui.py`, `scoda_package.py`)

Reference SPA 추출 관련 코드 제거 (더 이상 사용 안 함):
- `ScodaPackage.extract_spa()`, `get_spa_dir()`, `is_spa_extracted()`
- GUI의 "Extract Reference SPA" 버튼

### 6. 테스트 리팩터링 (`tests/`)

- `conftest.py` — 공유 fixture 정리, 패키지별 테스트 분리
- `test_runtime.py` — auto-discovery, entity detail 등 새 테스트 추가
- `test_mcp.py`, `test_trilobase.py` — 정리

## Manifest 업데이트

`trilobase.db` manifest에 추가된 필드:
- `genus_detail` > hierarchy: `data_key`, `link.detail_view`
- `genus_detail` > temporal_range: `mapping_key`, `link.detail_view`
- `taxonomy_tree` > options: `on_node_info.detail_view`
- `chronostratigraphy_table` > options: `cell_click.detail_view`

`scripts/add_scoda_manifest.py`도 동일하게 반영.

## 테스트

```
pytest tests/ -x -q → 231 passed
```
