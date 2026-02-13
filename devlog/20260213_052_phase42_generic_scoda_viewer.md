# Phase 42: Generic SCODA Package Viewer with Namespaced API

**날짜:** 2026-02-13
**상태:** 완료
**계획 문서:** `devlog/20260213_P36_generic_scoda_viewer.md`

## 목표

SCODA Desktop을 trilobase.scoda 전용 앱에서 **아무 `.scoda` 패키지를 열어서 UI를 자동 구성하는 범용 뷰어**로 전환.

## 변경 내용

### Phase A: PackageRegistry (`scoda_package.py`, +216줄)

- **`PackageRegistry` 클래스** 신규:
  - `scan(directory)`: `*.scoda` 파일 탐색, 없으면 `*.db` 폴백
  - `get_db(name)`: 패키지별 DB 연결 (overlay ATTACH + dependency ATTACH with alias)
  - `list_packages()`: 발견된 패키지 정보 리스트 반환
  - `get_package(name)`: 패키지 상세 정보 반환
  - `close_all()`: 모든 ScodaPackage 정리
- **`_ensure_overlay_for_package()`**: 패키지별 overlay DB 생성 (예: `paleocore_overlay.db`)
- **`get_registry()`**: 모듈 레벨 기본 레지스트리 (lazy init)
- **`_reset_registry()`**: 테스트 teardown용
- Dependency `alias` 지원: manifest의 `"alias": "pc"` → `ATTACH AS pc`
- 하위 호환: 기존 `get_db()`, `_set_paths_for_testing()`, `_reset_paths()` 변경 없음

### Phase A.1: `scripts/create_scoda.py` (+2줄)

- paleocore dependency에 `"alias": "pc"` 추가

### Phase B: Namespaced API Routes (`app.py`, +285줄 net)

**Core 헬퍼 함수 9개 추출** (legacy + namespaced 공용):
- `_fetch_manifest()`, `_fetch_metadata()`, `_fetch_provenance()`
- `_fetch_display_intent()`, `_fetch_queries()`, `_execute_query()`
- `_fetch_annotations()`, `_create_annotation()`, `_delete_annotation()`

**신규 엔드포인트:**
| 엔드포인트 | 설명 |
|-----------|------|
| `GET /api/packages` | 발견된 패키지 목록 |
| `GET /api/pkg/<name>/manifest` | 패키지 manifest |
| `GET /api/pkg/<name>/metadata` | 패키지 메타데이터 |
| `GET /api/pkg/<name>/provenance` | 패키지 출처 |
| `GET /api/pkg/<name>/display-intent` | display intent |
| `GET /api/pkg/<name>/queries` | named query 목록 |
| `GET /api/pkg/<name>/queries/<q>/execute` | query 실행 |
| `GET /api/pkg/<name>/annotations/<type>/<id>` | annotations 조회 |
| `POST /api/pkg/<name>/annotations` | annotation 생성 |
| `DELETE /api/pkg/<name>/annotations/<id>` | annotation 삭제 |

**Legacy 엔드포인트**: 내부만 core 헬퍼 호출로 리팩터링, API 동일.

### Phase C: Landing Page + Frontend (`index.html`, `app.js`, `style.css`)

- **Landing Page**: 패키지 카드 그리드 (`#landing-page`, `#package-grid`)
  - 패키지 1개: 자동 열기 (기존과 동일 동작)
  - 패키지 여러 개: 카드 선택 UI 표시
- **`apiBase` prefix**: 모든 SCODA 범용 fetch 호출에 적용
  - `/api/manifest` → `${apiBase}/manifest`
  - `/api/queries/.../execute` → `${apiBase}/queries/.../execute`
  - `/api/annotations/...` → `${apiBase}/annotations/...`
- **Navbar**: 패키지 제목 표시 (`#pkg-title`) + 뒤로가기 버튼 (`#pkg-back`)
- `loadPackages()`, `openPackage(name)`, `renderLandingPage()`, `showLandingPage()` 함수 추가
- Detail view의 `source` URL (예: `/api/genus/{id}`)은 manifest 정의 절대 경로이므로 변경 없음

### Phase D: GUI 갱신 (`scripts/gui.py`)

- `PackageRegistry.list_packages()` 기반 동적 표시
- Information 섹션: 발견된 모든 패키지 표시 (하드코딩 제거)
- 시작 로그: 각 패키지 이름/버전/레코드 수 출력

## 변경하지 않은 파일

- `mcp_server.py` — MCP는 기존 `get_db()` 사용 (trilobase 전용)
- `scripts/add_scoda_manifest.py` — manifest 내용 변경 없음
- `scripts/create_paleocore.py` — paleocore DB 생성 변경 없음

## 테스트

| 분류 | 테스트 수 | 상태 |
|------|---------|------|
| 기존 `test_app.py` | 185개 | 통과 |
| 신규 `TestPackageRegistry` | 8개 | 통과 |
| 신규 `TestPackagesEndpoint` | 3개 | 통과 |
| 신규 `TestNamespacedAPI` | 10개 | 통과 |
| `test_mcp_basic.py` | 1개 | 통과 |
| `test_mcp.py` | 16개 | 통과 |
| **합계** | **223개** | **전부 통과** |

### 신규 테스트 상세

**TestPackageRegistry (8개):**
- `test_scan_finds_scoda_files` — 디렉토리 스캔
- `test_open_package_db_connection` — 패키지 열기 + DB 연결
- `test_list_packages_returns_info` — 패키지 목록 필수 필드
- `test_dependency_resolution_with_alias` — dependency ATTACH with alias `pc`
- `test_package_without_deps` — 독립 패키지 (paleocore)
- `test_overlay_per_package` — 패키지별 overlay DB 생성
- `test_legacy_get_db_still_works` — 기존 get_db() 하위 호환
- `test_unknown_package_error` — 미존재 패키지 KeyError

**TestPackagesEndpoint (3개):**
- `test_packages_list_returns_200` — 200 응답
- `test_packages_returns_list` — 리스트 반환
- `test_packages_items_have_required_fields` — name/title/version 필드 존재

**TestNamespacedAPI (10개):**
- `test_pkg_manifest` — namespaced manifest 조회
- `test_pkg_manifest_equals_legacy` — legacy와 동일 구조 검증
- `test_pkg_queries` — query 목록
- `test_pkg_query_execute` — query 실행
- `test_pkg_metadata` — metadata 조회
- `test_pkg_provenance` — provenance 조회
- `test_pkg_display_intent` — display intent 조회
- `test_pkg_annotations_crud` — namespaced annotation CRUD
- `test_pkg_not_found` — 404 반환
- `test_pkg_query_not_found` — 404 반환

## 파일 변경 요약

| 파일 | 변경 |
|------|------|
| `scoda_package.py` | `PackageRegistry` 클래스 + `get_registry()` 추가 (+216줄) |
| `scripts/create_scoda.py` | dependency `alias` 추가 (+2줄) |
| `app.py` | core 헬퍼 9개 추출, namespaced routes 11개, `/api/packages` (+285줄 net) |
| `templates/index.html` | landing-page div, viewer-container wrapper, navbar 수정 (+21줄) |
| `static/js/app.js` | loadPackages, openPackage, apiBase prefix (+153줄) |
| `static/css/style.css` | landing page 카드 스타일 (+81줄) |
| `scripts/gui.py` | registry 기반 패키지 표시 (리팩터링) |
| `test_app.py` | 3개 테스트 클래스 21개 테스트 추가 (+404줄) |
