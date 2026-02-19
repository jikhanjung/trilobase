# Phase 44: Reference Implementation SPA

**날짜**: 2026-02-14
**상태**: 완료

## 작업 내용

Trilobase 전용 프론트엔드 코드를 "Reference Implementation SPA"로 분리하여 `.scoda` 패키지에 번들.
Built-in viewer는 generic SCODA viewer로 축소.

### 변경 요약

| 구분 | 설명 |
|------|------|
| Built-in viewer | Generic SCODA viewer (manifest-driven only, trilobase 전용 제거) |
| Reference SPA | `spa/` 디렉토리에 standalone 버전 (API_BASE prefix 지원) |
| 자동 전환 | 추출된 SPA 디렉토리 있으면 Flask가 자동 서빙 |
| 추출 | GUI "Extract Reference SPA" 버튼 |

## 신규 파일

| 파일 | 설명 |
|------|------|
| `spa/index.html` | Standalone HTML (Jinja2 없음, API_BASE 자동 감지) |
| `spa/app.js` | Full-featured JS (모든 fetch에 API_BASE prefix) |
| `spa/style.css` | Full CSS (rank 색상 포함) |

## 수정 파일

### `static/js/app.js` — Generic viewer로 축소
- Trilobase 전용 함수 제거:
  - `renderGenusGeography()`, `renderSynonymList()`, `renderRankStatistics()`, `renderRankChildren()`
  - `navigateToRank()`, `navigateToGenus()`
- `formatFieldValue()`: `hierarchy` → text join, `temporal_range` → `<code>` only
- `renderDetailSection()`: unknown type fallback → `renderLinkedTable()` (data_key가 배열인 경우)

### `static/css/style.css` — Rank 전용 CSS 제거
- `.rank-Class`, `.rank-Order`, `.rank-Suborder`, `.rank-Superfamily`, `.rank-Family` 색상 규칙 제거

### `scoda_package.py` — SPA 지원 확장
- `create()`: `extra_assets` 파라미터 추가 (dict of archive_path→local_path)
- `has_reference_spa` property: manifest 플래그 확인
- `get_spa_dir()`: 예상 SPA 추출 경로 반환
- `is_spa_extracted()`: 추출 완료 여부 확인
- `extract_spa(output_dir=None)`: assets/spa/ 파일 추출

### `scripts/create_scoda.py` — SPA 파일 패키징
- `spa/` 디렉토리 파일을 `extra_assets`로 전달
- `has_reference_spa: true`, `reference_spa_path: "assets/spa/"` manifest 추가

### `scripts/build.py` — SPA 포함 빌드
- `.scoda` 생성 시 `spa/` 파일 자동 포함

### `app.py` — 자동 전환 로직
- `_get_reference_spa_dir()`: 활성 패키지의 추출된 SPA 디렉토리 확인
- `index()`: SPA 추출되어 있으면 `send_from_directory()`, 아니면 generic viewer
- `serve_spa_file()`: SPA 에셋 파일 서빙 (`/<path:filename>`)

### `scripts/gui.py` — Extract Reference SPA 버튼
- "Extract Reference SPA" 버튼 추가 (has_reference_spa일 때만 활성)
- 이미 추출 시 확인 → 브라우저 열기 제안
- 미추출 시 추출 후 브라우저 열기 제안

### `ScodaDesktop.spec` — spa/ datas 추가
- `('spa', 'spa')` 항목 추가

### `test_app.py` — 신규 테스트 13개
- **TestScodaPackageSPA** (7개): create_with_spa, has_reference_spa, has_reference_spa_false_by_default, extract_spa, extract_spa_default_dir, is_spa_extracted, extract_no_spa_raises
- **TestFlaskAutoSwitch** (4개): index_generic_without_spa, index_reference_spa_when_extracted, spa_assets_served, api_routes_take_priority
- **TestGenericViewerFallback** (2개): index_serves_html, spa_404_for_nonexistent_files

## .scoda 패키지 구조

```
trilobase.scoda (ZIP)
├── manifest.json       # has_reference_spa: true
├── data.db
└── assets/
    └── spa/
        ├── index.html
        ├── app.js
        └── style.css
```

## 테스트 결과

| 파일 | 테스트 수 | 상태 |
|------|---------|------|
| `test_app.py` | 213개 (기존 200 + 신규 13) | 통과 |
| `test_mcp_basic.py` | 1개 | 통과 |
| `test_mcp.py` | 16개 | 통과 |
| **합계** | **230개** | **전부 통과** |
