# P37: Docker Desktop 스타일 컨트롤 패널 + 단일 패키지 서빙

**날짜:** 2026-02-13
**상태:** 계획

## 배경

Phase 42에서 namespaced API (`/api/pkg/<name>/...`)와 SPA landing page로 멀티 패키지를 지원했으나, 복잡도가 프론트엔드에 쏠림. **패키지 선택을 GUI 컨트롤 패널에서 처리**하고, Flask는 선택된 패키지만 서빙하도록 전환.

Docker Desktop이 컨테이너를 관리하는 것과 유사한 패턴.

## 핵심 변경

```
[Phase 42]  GUI → Flask (모든 패키지) → SPA Landing Page → 패키지 선택
[Phase 43]  GUI (패키지 선택) → Flask (선택된 패키지만) → SPA (바로 뷰어)
```

패키지 선택 책임: SPA → GUI(Tk)로 이동. Flask는 항상 하나의 패키지만 서빙.

## 구현 계획

### Phase 1: `scoda_package.py` — `set_active_package()` 추가

- `_active_package_name` 모듈 전역 변수
- `set_active_package(name)`: GUI/CLI가 호출
- `get_active_package_name()`: 현재 활성 패키지 조회
- `get_db()` 수정: `_active_package_name` 설정 시 registry 경유
- `_set_paths_for_testing()` / `_reset_paths()`: `_active_package_name = None` 추가

### Phase 2: `app.py` — namespaced routes 제거 + `/api/detail` 추가

**제거:**
- `get_registry` import
- `/api/packages` 엔드포인트
- `_get_pkg_conn()` 헬퍼
- namespaced routes 10개 (`/api/pkg/<name>/...`)

**추가:**
- `/api/detail/<query_name>`: named query 실행 → `rows[0]` flat JSON 반환
  - paleocore detail view의 source URL로 사용
- `__main__`에 `--package` CLI 인자

### Phase 3: `test_app.py` — 테스트 조정

- 제거: `TestPackagesEndpoint` (3개), `TestNamespacedAPI` (10개)
- 추가: `TestGenericDetailEndpoint` (5개), `TestPackageRegistry` +2개
- 예상: ~196개

### Phase 4: `scripts/gui.py` — Docker Desktop 스타일 UI

- 왼쪽 패널: 선택 가능한 패키지 Listbox + 선택 정보
- 패키지 1개: 자동 선택 + 자동 시작 (기존 UX 유지)
- 패키지 여러 개: 목록 표시, 사용자 선택 대기
- `_start_server_subprocess`: `--package <name>` 인자 전달
- `_start_server_threaded`: `set_active_package(name)` 호출
- Flask 실행 중 패키지 전환 방지 (Listbox 비활성화)

### Phase 5: Frontend 단순화

- 제거: `currentPackage`, `apiBase`, `loadPackages()`, `openPackage()`, `renderLandingPage()`, `showLandingPage()`
- 제거: `#landing-page` div, `#pkg-title`, `#pkg-back`, `#viewer-container` wrapper
- 제거: landing page CSS (~81줄)
- `DOMContentLoaded` → `loadManifest()` + `loadTree()` 직접 호출
- `apiBase` 패턴 11곳 → `/api/...` 직접 URL

### Phase 6: PaleoCore detail view 추가

- `scripts/create_paleocore.py`에 detail query 3개 + detail view 3개 추가
  - `country_detail`, `formation_detail`, `chronostrat_detail`
- table view에 `on_row_click` 추가
- source: `/api/detail/<query>?id={id}` 패턴
- paleocore.db + paleocore.scoda 재생성

### Phase 7: `scripts/serve.py` — `--package` 인자 추가

### Phase 8: .scoda 패키지 재빌드

## 파일 변경 요약

| 파일 | 변경 |
|------|------|
| `scoda_package.py` | `set_active_package()`, `get_db()` 수정 |
| `app.py` | namespaced routes 제거, `/api/detail` 추가, `--package` CLI |
| `test_app.py` | 테스트 제거/추가 |
| `scripts/gui.py` | 패키지 Listbox, 선택 핸들러, start/stop 수정 |
| `static/js/app.js` | landing page/apiBase 제거 |
| `templates/index.html` | landing page 관련 HTML 제거 |
| `static/css/style.css` | landing page 스타일 제거 |
| `scripts/create_paleocore.py` | detail query/view 추가 |
| `scripts/serve.py` | `--package` CLI 추가 |

## 검증 방법

1. `pytest test_app.py test_mcp_basic.py test_mcp.py` — 전체 통과
2. `python app.py --package trilobase` → 기존 trilobase UI 동일
3. `python app.py --package paleocore` → paleocore 4개 탭 + detail
4. `python scripts/gui.py` → 패키지 목록, 선택, Start/Stop
5. `python app.py` (인자 없음) → 레거시 호환
