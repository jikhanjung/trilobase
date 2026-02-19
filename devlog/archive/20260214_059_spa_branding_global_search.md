# Reference SPA: 브랜딩 변경 + 글로벌 검색 추가

**날짜:** 2026-02-14
**계획:** `devlog/20260214_P41_spa_branding_global_search.md`

## 변경 사항

### 1. 브랜딩 변경 (`spa/index.html`)

- `<title>` SCODA Desktop → Trilobase
- Navbar: 아이콘 `bi-diagram-3` → `bi-bug`, 텍스트 → "Trilobase" + 부제 "A SCODA Package"

### 2. 글로벌 검색 UI (`spa/index.html`, `spa/style.css`)

- `view-tabs`를 `view-tabs-bar` flexbox 래퍼로 감싸고 오른쪽에 검색 input 배치
- 검색 드롭다운: 480px 너비, max-height 520px, z-index 1050
- 카테고리별 헤더 (아이콘 + 이름 + 건수)
- 결과 항목: hover/highlight, `<mark>` 하이라이트 (#fff3cd 배경)
- "+N more" 확장 클릭
- `Ctrl+K` 단축키 표시 badge

### 3. 검색 로직 (`spa/app.js`)

- **6개 검색 카테고리**: Genera, Taxonomy, Formations, Countries, Bibliography, Chronostratigraphy
- **클라이언트 사이드 검색**: 기존 named query 재활용, 백엔드 변경 없음
- `preloadSearchIndex()`: 6개 query 병렬 fetch → `_searchText` 사전 계산
- `performSearch()`: 200ms debounce, 2글자 최소, multi-term AND 매칭, prefix match 우선 정렬
- 결과 제한: genera 6건, 나머지 4건 기본 표시, "+N more" 확장
- 키보드 네비게이션: ArrowUp/Down 이동, Enter 선택, Escape 닫기
- `Ctrl+K` / `Cmd+K` 단축키로 검색 포커스
- 외부 클릭 시 드롭다운 닫기
- `escapeHtml()` XSS 방지 유틸 추가

### 4. 공유 쿼리 캐시 (`spa/app.js`)

- `queryCache` + `fetchQuery()` 헬퍼 도입
- 검색 인덱스와 탭 뷰가 동일 데이터 공유 (중복 fetch 제거)
- `renderTableView()`, `loadTree()`, `renderChronostratChart()` → `fetchQuery()` 전환
- `setTimeout(500)` 제거 → 페이지 로드 시 즉시 preload
- 탭 전환 시 네트워크 요청 없이 캐시에서 즉시 렌더링

## 변경 파일

| 파일 | 변경 내용 |
|------|----------|
| `spa/index.html` | 브랜딩 변경 + 검색 input HTML 추가 |
| `spa/style.css` | view-tabs-bar 래퍼 + 검색 드롭다운 스타일 |
| `spa/app.js` | queryCache, fetchQuery, 검색 로직 (~300줄 추가) |

## 테스트

- 188개 통과 (test_runtime 135 + test_trilobase 51 + test_mcp_basic 1 + test_mcp 1 skip)
- SPA 관련 테스트 11개 통과
- 백엔드 변경 없음
