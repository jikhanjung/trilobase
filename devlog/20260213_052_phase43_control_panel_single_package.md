# Phase 43: Docker Desktop Style Control Panel + Single Package Serving

**날짜**: 2026-02-13

## 작업 내용

Phase 42에서 도입한 namespaced API (`/api/pkg/<name>/...`)와 SPA landing page를 제거하고,
패키지 선택 책임을 GUI(Tk)로 이동. Flask는 선택된 패키지 하나만 서빙하도록 전환.
Docker Desktop이 컨테이너를 관리하는 패턴과 유사.

## 변경 파일

### scoda_package.py (+26줄)
- `_active_package_name` 모듈 전역 변수 추가
- `set_active_package(name)`: GUI/CLI가 호출하여 활성 패키지 설정
- `get_active_package_name()`: 현재 활성 패키지 반환
- `get_db()`: `_active_package_name` 설정 시 registry 경유, 미설정 시 레거시 동작
- `_set_paths_for_testing()`, `_reset_paths()`: `_active_package_name = None` 추가

### app.py (-133줄, +12줄)
- **제거**: `/api/packages`, `_get_pkg_conn()`, namespaced routes 10개 (~120줄)
- **추가**: `/api/detail/<query_name>` — named query 실행 → 첫 행 flat JSON 반환
- **추가**: `--package` CLI 인자 (argparse)
- `get_registry` import 제거

### test_app.py (-208줄, +7개 테스트)
- **제거**: `TestPackagesEndpoint` (3개), `TestNamespacedAPI` (10개) = 13개
- **추가**: `TestGenericDetailEndpoint` (5개): detail 반환, params, 404, SQL error
- **추가**: `TestActivePackage` (2개): registry 경유, testing 초기화

### scripts/gui.py (전면 개편)
- 왼쪽 패널: 정적 Information → **Packages Listbox** (선택 가능)
- `selected_package` 상태 추가
- `_on_package_select()`: 실행 중이면 전환 차단, Listbox 재선택
- `_update_pkg_info()`: 선택된 패키지 정보 표시
- `start_server()`: `selected_package` 필수 검증
- `_start_server_subprocess()`: `--package` 인자 전달
- `_start_server_threaded()`: `set_active_package()` 호출
- `_update_status()`: 실행 중 Listbox 비활성화
- 자동 선택/시작: 패키지 1개면 auto-select + 500ms 후 auto-start

### static/js/app.js (-146줄)
- `currentPackage`, `apiBase` 변수 제거
- `loadPackages()`, `openPackage()`, `renderLandingPage()`, `showLandingPage()` 제거
- `DOMContentLoaded`: `loadManifest()` + `loadTree()` 직접 호출
- `loadManifest()`: 직접 `/api/manifest` 호출
- 11곳 `apiBase` 3항 연산자 → 직접 `/api/...` URL로 단순화

### templates/index.html (-19줄)
- `#pkg-title` span, `#pkg-back` link 제거
- `#landing-page` div 제거
- `#viewer-container` wrapper div 제거

### static/css/style.css (-81줄)
- `.landing-header`, `.package-grid`, `.package-card` 관련 스타일 전부 제거
- `.navbar-pkg-title`, `#pkg-back` 스타일 제거

### scripts/create_paleocore.py (+76줄)
- Detail query 3개 추가: `country_detail`, `formation_detail`, `chronostrat_detail`
- Manifest에 `on_row_click` 추가: countries_table, formations_table
- Manifest에 `chart_options.cell_click` 추가: chronostratigraphy_chart
- Detail view 3개 추가: country_detail, formation_detail, chronostrat_detail

### scripts/serve.py (+8줄)
- `--package` argparse 인자 추가
- 패키지 지정 시 `set_active_package()` 호출

### paleocore.db
- ui_queries: 8 → 11개 (3개 detail query 추가)
- ui_manifest: 4 → 7개 views (3개 detail view + on_row_click 추가)

## 테스트 결과

```
pytest test_app.py test_mcp_basic.py test_mcp.py
217 passed in 146.55s
```

## 동작 확인

1. `python app.py --package trilobase` → 기존과 동일한 trilobase UI
2. `python app.py --package paleocore` → 4개 탭 + detail 클릭 동작
3. `python app.py` (--package 없이) → 레거시 trilobase 동작
4. GUI: 패키지 목록 표시, 선택, Start/Stop 동작
