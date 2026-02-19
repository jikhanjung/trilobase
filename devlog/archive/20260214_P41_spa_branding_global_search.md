# Plan: Trilobase SPA 브랜딩 변경 + 글로벌 검색

**날짜:** 2026-02-14
**유형:** Plan

## 배경

Reference SPA는 Trilobase SCODA 패키지 전용 프론트엔드인데, 현재 "SCODA Desktop"으로 표시됨.
Trilobase 패키지를 보여주는 페이지임을 강조하도록 브랜딩을 변경하고,
탭 바에 글로벌 검색 인터페이스를 추가하여 모든 엔티티를 종합 검색 가능하게 함.

## 변경 파일

- `spa/index.html` — 브랜딩 + 검색 input HTML 추가
- `spa/style.css` — 검색 드롭다운 스타일
- `spa/app.js` — 검색 로직 (preload, search, render, keyboard nav)
- **백엔드 변경 없음** — 기존 named query 재활용

## 1. 브랜딩 변경 (`spa/index.html`)

- `<title>SCODA Desktop</title>` → `<title>Trilobase</title>`
- Navbar: `SCODA Desktop` → `Trilobase` + 부제 "A SCODA Package"
- 아이콘: `bi-diagram-3` → `bi-bug` (삼엽충에 더 적합)

## 2. 탭 바에 검색 input 추가 (`spa/index.html`)

기존 `<div class="view-tabs" id="view-tabs"></div>` 구조를 래퍼로 감싸고 오른쪽에 검색 input 배치:

```html
<div class="view-tabs-bar">
    <div class="view-tabs" id="view-tabs"></div>
    <div class="global-search-container">
        <div class="global-search-wrapper">
            <i class="bi bi-search"></i>
            <input type="text" id="global-search-input"
                   placeholder="Search genera, formations, references..."
                   autocomplete="off">
            <kbd class="global-search-shortcut">Ctrl+K</kbd>
        </div>
        <div class="global-search-results" id="global-search-results"></div>
    </div>
</div>
```

## 3. CSS (`spa/style.css`)

- `.view-tabs-bar`: flexbox 래퍼 (tabs + search)
- `.view-tabs`: border-bottom 제거 (부모가 처리)
- `.global-search-wrapper`: 260px, 아이콘 prefix
- `.global-search-results`: absolute 드롭다운 (480px, max-height 520px, z-index 1050)
- `.search-category-header`: 카테고리별 구분 (아이콘 + 이름 + 건수)
- `.search-result-item`: 클릭 가능 행 (hover/highlight 스타일)
- `mark` 태그로 매치 하이라이트 (#fff3cd 배경)
- `.view-tabs:not(:empty) ~ .view-container` → `.view-tabs-bar ~ .view-container`로 수정

## 4. JavaScript 검색 로직 (`spa/app.js`)

### 전략: 클라이언트 사이드 검색 + lazy preload

- 총 ~9,800건 (genera 5,115 + taxonomy 225 + bibliography 2,130 + formations ~800 + countries ~60 + ICS 178)
- 페이지 로드 500ms 후 6개 named query를 **병렬 fetch**하여 메모리 인덱스 구축
- 검색은 `String.includes()` 기반 — 10K건에서 <5ms
- **백엔드 변경 불필요** (기존 `/api/queries/<name>/execute` 그대로 사용)

### 검색 카테고리 (6개)

| Category | Named Query | 검색 대상 필드 | Detail View | 아이콘 |
|----------|-------------|---------------|-------------|--------|
| Genera | `genera_list` | name, author, family | `genus_detail` | bi-bug |
| Taxonomy | `taxonomy_tree` | name, rank | `rank_detail` | bi-diagram-3 |
| Formations | `formations_list` | name, country, period | `formation_detail` | bi-layers |
| Countries | `countries_list` | name | `country_detail` | bi-globe |
| Bibliography | `bibliography_list` | authors, title | `bibliography_detail` | bi-book |
| Chronostratigraphy | `ics_chronostrat_list` | name | `chronostrat_detail` | bi-clock-history |

### 주요 함수

1. **`initGlobalSearch()`** — input 이벤트 리스너 등록 + Ctrl+K 단축키 + 외부 클릭 닫기
2. **`preloadSearchIndex()`** — 6개 query 병렬 fetch → 각 row에 `_searchText` (lowercase concat) 사전 계산
3. **`performSearch(query)`** — 200ms debounce, 2글자 최소, multi-term AND 매칭, prefix match 우선 정렬
4. **`renderSearchResults()`** — 카테고리별 그룹 표시 (genera 6건, 나머지 4건 기본, "+N more" 확장)
5. **키보드 네비게이션** — ArrowUp/Down으로 결과 이동, Enter로 선택, Escape로 닫기
6. **`onSearchResultClick()`** — `hideSearchResults()` + `openDetail(viewKey, id)` 호출

### DOMContentLoaded 수정

기존 핸들러 끝에 추가:
```javascript
initGlobalSearch();
setTimeout(preloadSearchIndex, 500);
```

## 5. 기존 유틸 재사용

- `truncate()` (app.js:936) — bibliography displayMeta
- `openDetail()` (app.js:1083) — 검색 결과 클릭 시 상세 모달
- `escapeHtml()` 신규 추가 필요 (XSS 방지)
