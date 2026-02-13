# Plan: Declarative Manifest Schema + UI Migration

**작성일:** 2026-02-13
**Phase:** 39 (a-e)

## 배경

현재 SCODA Desktop 뷰어의 `app.js`(1,661줄)에 7개 detail 모달 함수가 하드코딩되어 있다.
DB에 `ui_manifest` 테이블이 있지만 table/tree/chart 뷰만 정의하고, detail 뷰는 선언만 있을 뿐 렌더링에 사용되지 않는다.
테이블 행 클릭도 `clickHandlers` map에 하드코딩되어 있다.

**목표**: manifest에 detail view 스키마를 확장하고, `app.js`의 하드코딩된 렌더링 로직을 manifest 기반 범용 렌더러로 교체한다. 결과적으로 `.scoda` 패키지만으로 모든 UI가 정의되는 범용 SCODA 뷰어가 된다.

## 현재 상태

- `ui_manifest` DB: 7개 뷰 (tree 1, table 4, detail 1, chart 1)
- `add_scoda_manifest.py`: 6개만 정의 (chronostratigraphy_table 누락 — Phase 30에서 DB만 업데이트)
- `app.js` hardcoded: showGenusDetail, showCountryDetail, showRegionDetail, showFormationDetail, showBibliographyDetail, showChronostratDetail, showRankDetail
- `clickHandlers` map: 5개 table view → detail function 매핑

## 파일 변경 목록

| 파일 | 변경 내용 |
|------|-----------|
| `scripts/add_scoda_manifest.py` | 7개 detail view 추가, table view에 on_row_click 추가, chronostratigraphy_table 추가 |
| `static/js/app.js` | 범용 detail 렌더러 추가 → 7개 detail 함수 교체 → clickHandlers 제거 |
| `trilobase.db` | 스크립트 재실행으로 ui_manifest 업데이트 |
| `test_app.py` | test fixture 업데이트, manifest schema 테스트 추가 |

`app.py`는 변경 없음 (모든 API 엔드포인트 이미 존재).

---

## Phase 39a: Manifest Schema 확장

**`scripts/add_scoda_manifest.py`** 수정:

1. `chronostratigraphy_table` 뷰 추가 (현재 DB에만 있고 스크립트에 없음)
2. 모든 table view에 `on_row_click` 추가:
   ```json
   "on_row_click": {"detail_view": "country_detail", "id_key": "id"}
   ```
3. 7개 detail view 추가:
   - `formation_detail` — field_grid(6 fields) + linked_table(genera)
   - `country_detail` — field_grid(3) + linked_table(regions) + linked_table(genera, region 링크 포함)
   - `region_detail` — field_grid(3, country 링크) + linked_table(genera)
   - `bibliography_detail` — field_grid(11, conditional fields) + raw_text + linked_table(genera)
   - `chronostrat_detail` — field_grid(6, color_chip/boolean) + field_grid(hierarchy) + linked_table(children) + tagged_list(mappings) + linked_table(genera)
   - `genus_detail` (기존 교체) — field_grid(6, hierarchy/temporal_range) + field_grid(type_species) + genus_geography(built-in) + synonym_list(built-in) + raw_text(notes) + raw_text(raw_entry) + annotations
   - `rank_detail` — field_grid(5) + rank_statistics(built-in) + rank_children(built-in) + raw_text(notes) + annotations

4. `trilobase.db` 업데이트 (스크립트 재실행)

### Detail View 공통 스키마

```json
{
  "type": "detail",
  "source": "/api/formation/{id}",
  "icon": "bi-layers",
  "title_template": {"format": "{icon} {name}"},
  "sections": [
    {
      "title": "Basic Information",
      "type": "field_grid",
      "fields": [
        {"key": "name", "label": "Name", "format": "italic"},
        {"key": "is_valid", "label": "Status", "format": "boolean", "true_label": "Valid", "false_label": "Invalid"}
      ]
    },
    {
      "title": "Genera ({count})",
      "type": "linked_table",
      "data_key": "genera",
      "columns": [
        {"key": "name", "label": "Genus", "italic": true},
        {"key": "author", "label": "Author"},
        {"key": "year", "label": "Year"},
        {"key": "is_valid", "label": "Valid", "format": "boolean"}
      ],
      "on_row_click": {"detail_view": "genus_detail", "id_key": "id"}
    }
  ]
}
```

### Section types

| type | 용도 | 필수 필드 |
|------|------|-----------|
| `field_grid` | 라벨-값 2열 그리드 | `fields[]` |
| `linked_table` | 관련 데이터 테이블 | `data_key`, `columns[]`, `on_row_click` |
| `tagged_list` | 배지+텍스트 리스트 | `data_key`, `badge_key`, `text_key` |
| `raw_text` | 모노스페이스 텍스트 블록 | `data_key` |
| `annotations` | My Notes CRUD | `entity_type` or `entity_type_from` |
| `genus_geography` | 국가/지층 링크 (built-in) | — |
| `synonym_list` | 동의어 배지+링크 (built-in) | `data_key` |
| `rank_statistics` | 하위 분류 통계 (built-in) | — |
| `rank_children` | 하위 분류군 목록 (built-in) | `data_key` |

### Field format types

| format | 렌더링 |
|--------|--------|
| `italic` | `<i>값</i>` |
| `boolean` | true_label / false_label |
| `link` | 클릭 가능 링크 → 다른 detail view |
| `color_chip` | 색상 칩 + hex |
| `code` | `<code>값</code>` |
| `hierarchy` | 계층 breadcrumb (built-in) |
| `temporal_range` | 시대코드 + ICS 링크 (built-in) |
| `computed:time_range` | start_mya–end_mya Ma 계산 |

---

## Phase 39b: 범용 Detail 렌더러 구현

**`static/js/app.js`**에 새 함수 추가 (~300줄, 기존 코드 변경 없음):

1. **`openDetail(viewKey, entityId)`** — manifest에서 view 찾아 렌더링 또는 기존 함수 fallback
2. **`renderDetailFromManifest(viewKey, entityId)`** — API fetch → section별 렌더링
3. **`buildDetailTitle(template, data)`** — title 템플릿 interpolation
4. **`renderDetailSection(section, data)`** — type별 dispatch
5. **`renderFieldGrid(section, data)`** — field format 적용
6. **`renderLinkedTable(section, data)`** — 테이블 + on_row_click
7. **`renderTaggedList(section, data)`** — badge list
8. **`renderRawText(section, data)`** — monospace block
9. **`resolveDataPath(data, path)`** — "parent.name" 같은 dot path 해석
10. **Built-in renderers** (기존 로직 추출):
    - `renderGenusGeography(data)` — showGenusDetail에서 추출
    - `renderSynonymList(section, data)` — showGenusDetail에서 추출
    - `renderRankStatistics(data)` — showRankDetail에서 추출
    - `renderRankChildren(section, data)` — showRankDetail에서 추출

이 단계에서는 새 함수만 추가하고, 기존 show*Detail 함수는 그대로 유지한다.

---

## Phase 39c: Detail 함수 마이그레이션 (단순→복잡 순)

기존 함수 본문을 `renderDetailFromManifest` 호출로 교체. 함수 시그니처는 유지 (기존 caller 호환):

1. **showFormationDetail** → `renderDetailFromManifest('formation_detail', id)`
2. **showRegionDetail** → `renderDetailFromManifest('region_detail', id)`
3. **showCountryDetail** → `renderDetailFromManifest('country_detail', id)`
4. **showBibliographyDetail** → `renderDetailFromManifest('bibliography_detail', id)`
5. **showChronostratDetail** → `renderDetailFromManifest('chronostrat_detail', id)`
6. **showGenusDetail** → `renderDetailFromManifest('genus_detail', id)`
7. **showRankDetail** → `renderDetailFromManifest('rank_detail', id)`

각 함수 교체 후 수동 확인. 모든 교체 후 구 코드 삭제.

---

## Phase 39d: Table clickHandlers 제거

`renderTableViewRows()`의 하드코딩 `clickHandlers` map 삭제, manifest `on_row_click`으로 교체:

```javascript
// Before:
const clickHandlers = { 'countries_table': (row) => `onclick="showCountryDetail(${row.id})"`, ... };
const getClick = clickHandlers[viewKey];

// After:
const view = manifest.views[viewKey];
const rowClick = view.on_row_click;
const getClick = rowClick
    ? (row) => `onclick="openDetail('${rowClick.detail_view}', ${row[rowClick.id_key]})"`
    : null;
```

Tree view와 chart view의 하드코딩 onclick도 `openDetail` 호출로 교체.

---

## Phase 39e: 테스트 + 문서

**`test_app.py`**:
- test fixture에 detail view 정의 + on_row_click 추가
- `TestManifestDetailSchema` 클래스 (~15 tests): view 구조 검증
- 기존 테스트 업데이트 (view count 등)

**devlog + HANDOVER.md 갱신**

---

## 검증 방법

1. `python scripts/add_scoda_manifest.py` — DB manifest 업데이트
2. `python -m flask run` — 웹 앱 실행
3. 모든 탭 클릭, 각 행 클릭 → detail 모달 정상 표시 확인
4. Genus detail: hierarchy, type species, geography, synonymy, notes, raw entry, annotations 확인
5. Rank detail: statistics, children, annotations 확인
6. `pytest test_app.py test_mcp_basic.py test_mcp.py` — 전체 테스트 통과

## 리스크

- **Genus detail 복잡도**: geography(country/region fallback), synonym(badge+link), temporal ICS mapping 등이 복잡. Built-in renderer로 기존 로직 보존.
- **Rank detail entity_type**: annotations의 entity_type이 동적 (rank 값에서 파생). `entity_type_from: "rank"` 설정으로 해결.
- **Tree view navigateToGenus/navigateToRank**: tree expansion 로직은 변경하지 않음. click handler만 교체.
