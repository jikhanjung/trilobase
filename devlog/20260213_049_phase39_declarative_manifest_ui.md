# Phase 39: Declarative Manifest Schema + UI Migration

**작성일:** 2026-02-13
**계획 문서:** `devlog/20260213_P33_declarative_manifest_ui_migration.md`

## 목표

`app.js`의 하드코딩된 detail 모달 렌더링 로직을 `ui_manifest`의 선언적 스키마 기반 범용 렌더러로 교체.
결과: `.scoda` 패키지의 manifest만으로 모든 UI가 정의되는 범용 SCODA 뷰어.

## 완료 내용

### Phase 39a: Manifest Schema 확장
- `scripts/add_scoda_manifest.py` 확장: 6 → 13개 뷰 (tab 6 + detail 7)
- 7개 detail view 추가: formation, country, region, bibliography, chronostrat, genus, rank
- Table view에 `on_row_click` 추가 (manifest-driven 네비게이션)
- `chronostratigraphy_table` 스크립트에 추가 (Phase 30에서 DB만 업데이트되었던 것)
- Chart view에 `chart_options` 추가

### Phase 39b: 범용 Detail 렌더러 구현
`app.js`에 manifest-driven 렌더러 함수 추가:
- `openDetail(viewKey, entityId)` — 엔트리 포인트
- `renderDetailFromManifest(viewKey, entityId)` — API fetch → section 렌더링
- `renderFieldGrid`, `renderLinkedTable`, `renderTaggedList`, `renderRawText` — 범용 section 렌더러
- `renderGenusGeography`, `renderSynonymList`, `renderRankStatistics`, `renderRankChildren` — built-in 렌더러
- `formatFieldValue` — italic, boolean, link, color_chip, code, hierarchy, temporal_range 포맷
- `resolveDataPath` — dot notation (e.g., "parent.name") 지원
- `buildDetailTitle` — 템플릿 기반 모달 타이틀 생성

### Phase 39c: Detail 함수 마이그레이션
7개 함수 본문을 `renderDetailFromManifest` 호출 1줄로 교체:
1. `showFormationDetail` → `renderDetailFromManifest('formation_detail', id)`
2. `showRegionDetail` → `renderDetailFromManifest('region_detail', id)`
3. `showCountryDetail` → `renderDetailFromManifest('country_detail', id)`
4. `showBibliographyDetail` → `renderDetailFromManifest('bibliography_detail', id)`
5. `showChronostratDetail` → `renderDetailFromManifest('chronostrat_detail', id)`
6. `showGenusDetail` → `renderDetailFromManifest('genus_detail', id)`
7. `showRankDetail` → `renderDetailFromManifest('rank_detail', id)`

### Phase 39d: Table clickHandlers 제거
- `clickHandlers` map 삭제, manifest `on_row_click`으로 교체
- Tree view info 버튼: `showRankDetail()` → `openDetail('rank_detail', ...)`
- Chart cell click: `showChronostratDetail()` → `openDetail('chronostrat_detail', ...)`
- Tree genera list: `showGenusDetail()` → `openDetail('genus_detail', ...)`
- `navigateToRank`, `navigateToGenus`: `openDetail` 호출로 교체
- `buildHierarchyHTML`, `buildTemporalRangeHTML`: `openDetail` 호출로 교체

### Phase 39e: 테스트 + 문서
- `test_app.py` fixture: 13개 뷰로 확장, `countries_list`/`formations_list` 쿼리 추가
- `TestManifestDetailSchema` 클래스 (14개 신규 테스트)
- 기존 테스트 업데이트 (view count 5→13, query count 6→8)

## 결과

### Section Types (9개)

| type | 용도 |
|------|------|
| `field_grid` | 라벨-값 2열 그리드 |
| `linked_table` | 관련 데이터 테이블 |
| `tagged_list` | 배지+텍스트 리스트 |
| `raw_text` | 모노스페이스/paragraph 텍스트 |
| `annotations` | My Notes CRUD |
| `genus_geography` | 국가/지층 링크 (built-in) |
| `synonym_list` | 동의어 배지+링크 (built-in) |
| `rank_statistics` | 하위 분류 통계 (built-in) |
| `rank_children` | 하위 분류군 목록 (built-in) |

### Field Format Types (8개)

| format | 렌더링 |
|--------|--------|
| `italic` | `<i>값</i>` |
| `boolean` | true_label / false_label |
| `link` | 클릭 가능 링크 → detail view |
| `color_chip` | 색상 칩 + hex |
| `code` | `<code>값</code>` |
| `hierarchy` | 계층 breadcrumb (built-in) |
| `temporal_range` | 시대코드 + ICS 링크 (built-in) |
| `computed` | 파생 값 (time_range 등) |

### 코드 변화
- `app.js`: 1,661줄 → 1,473줄 (-188줄, 범용 렌더러 +300줄, 하드코딩 제거 -488줄)
- `add_scoda_manifest.py`: 6 → 13개 뷰

### 테스트
- 192개 전부 통과 (기존 178 + 신규 14)
  - `test_app.py`: 175개
  - `test_mcp_basic.py`: 1개
  - `test_mcp.py`: 16개
