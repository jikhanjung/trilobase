# Plan: Generic SCODA Package Viewer with Namespaced API

**Date:** 2026-02-13
**Status:** Plan

## Context

SCODA Desktop은 현재 trilobase.scoda 전용 앱. `scoda_package.py`가 `trilobase.scoda`/`paleocore.scoda` 파일명을 하드코딩하고, `app.py`의 API 엔드포인트도 trilobase 테이블 구조에 직접 의존.

**목표**: 아무 `.scoda` 패키지를 열어서 그 안의 `ui_manifest`로 UI를 자동 구성하는 범용 뷰어로 전환.

**사용자 결정**:
1. Landing page 방식 — 디렉토리 내 `.scoda` 파일 목록 표시, 하나면 자동 열기
2. 기존 엔드포인트 유지 + `/api/pkg/<name>/...` namespace 추가

## 핵심 전략

```
[현재]  trilobase.scoda (하드코딩) → get_db() → 단일 연결
[변경]  PackageRegistry → 여러 .scoda 탐색 → /api/pkg/<name>/... 으로 접근
        Landing page → 패키지 선택 → 해당 manifest로 UI 구성
```

---

## Phase A: PackageRegistry (scoda_package.py)

### 새 클래스: `PackageRegistry`

```python
class PackageRegistry:
    """Discover and manage multiple .scoda packages."""

    def __init__(self):
        self._packages = {}   # name → {pkg: ScodaPackage, db_path, overlay_path, deps: [...]}
        self._scan_dir = None

    def scan(self, directory):
        """디렉토리 내 *.scoda 파일 탐색, 각 manifest.json 읽기."""
        # glob('*.scoda') → ScodaPackage 열기 → name 추출 → 등록
        # .scoda 없으면 *.db 폴백 (trilobase.db, paleocore.db)

    def get_db(self, name):
        """패키지별 DB 연결 반환. dependency ATTACH + overlay ATTACH."""
        # 1. sqlite3.connect(pkg.db_path)
        # 2. manifest.json의 dependencies 순회
        #    - 각 dep: self._packages[dep.name].db_path를 ATTACH AS dep.alias
        # 3. overlay DB ATTACH (per-package: <name>_overlay.db)

    def list_packages(self):
        """발견된 패키지 목록 반환."""
        # [{name, title, version, record_count, description, has_dependencies}, ...]

    def get_package(self, name):
        """패키지 정보 반환."""

    def close_all(self):
        """모든 ScodaPackage 정리."""
```

### Dependency alias 지원

trilobase의 SQL은 `pc.*` prefix를 사용하지만 dependency 이름은 `paleocore`. 매핑 필요:

```json
// scripts/create_scoda.py의 trilobase manifest.json
"dependencies": [{
    "name": "paleocore",
    "alias": "pc",           // ← 추가: ATTACH AS pc
    "version": "0.3.0",
    "file": "paleocore.scoda"
}]
```

`PackageRegistry.get_db(name)`에서:
```python
for dep in manifest_deps:
    alias = dep.get('alias', dep['name'])
    conn.execute(f"ATTACH DATABASE '{dep_db_path}' AS {alias}")
```

### Overlay DB per-package

현재: `trilobase_overlay.db` 하드코딩
변경: `<package_name>_overlay.db` (예: `paleocore_overlay.db`)

### 하위 호환

- 기존 `get_db()` 함수 유지 → default registry의 trilobase 패키지 연결 반환
- `_set_paths_for_testing()` / `_reset_paths()` 그대로 유지 (테스트 bypass)
- 새 public API: `get_registry() → PackageRegistry`

### 파일 변경

| 파일 | 변경 |
|------|------|
| `scoda_package.py` | `PackageRegistry` 클래스 추가 (+~150줄), `get_registry()` 추가 |
| `scripts/create_scoda.py` | dependency에 `"alias": "pc"` 추가 (+1줄) |

---

## Phase B: Namespaced API Routes (app.py)

### 새 엔드포인트

```
GET  /api/packages                                    → 발견된 패키지 목록
GET  /api/pkg/<name>/manifest                         → 패키지 manifest
GET  /api/pkg/<name>/metadata                         → 패키지 메타데이터
GET  /api/pkg/<name>/provenance                       → 패키지 출처
GET  /api/pkg/<name>/display-intent                   → display intent
GET  /api/pkg/<name>/queries                          → named query 목록
GET  /api/pkg/<name>/queries/<query>/execute          → query 실행
GET  /api/pkg/<name>/annotations/<type>/<id>          → annotations 조회
POST /api/pkg/<name>/annotations                      → annotation 생성
DELETE /api/pkg/<name>/annotations/<id>               → annotation 삭제
```

### DRY 리팩터링 — core 함수 추출

기존 route 로직을 `_core_xxx(conn)` 헬퍼로 추출, legacy + namespaced 둘 다 사용:

```python
def _fetch_manifest(conn):
    """conn에서 manifest 읽어 dict 반환."""
    cursor = conn.cursor()
    cursor.execute("SELECT ... FROM ui_manifest WHERE name = 'default'")
    ...

# Legacy (변경 없음 — 내부만 _fetch_manifest 호출로 변경)
@app.route('/api/manifest')
def api_manifest():
    conn = get_db()
    result = _fetch_manifest(conn)
    conn.close()
    return jsonify(result) if result else (jsonify({'error': '...'}), 404)

# Namespaced (신규)
@app.route('/api/pkg/<pkg_name>/manifest')
def api_pkg_manifest(pkg_name):
    registry = get_registry()
    try:
        conn = registry.get_db(pkg_name)
    except KeyError:
        return jsonify({'error': f'Package not found: {pkg_name}'}), 404
    result = _fetch_manifest(conn)
    conn.close()
    return jsonify(result) if result else (jsonify({'error': '...'}), 404)
```

이 패턴을 6개 SCODA 범용 엔드포인트에 적용: manifest, metadata, provenance, display-intent, queries, queries/execute

### Trilobase 전용 엔드포인트 — 변경 없음

`/api/tree`, `/api/genus/<id>`, `/api/family/<id>/genera`, `/api/rank/<id>`, `/api/country/<id>`, `/api/region/<id>`, `/api/formation/<id>`, `/api/bibliography/<id>`, `/api/chronostrat/<id>` — 전부 그대로. trilobase가 로드되어 있을 때만 동작.

### 파일 변경

| 파일 | 변경 |
|------|------|
| `app.py` | core 헬퍼 6개 추출, namespaced routes 10개 추가, `/api/packages` 추가 (+~130줄) |

---

## Phase C: Landing Page + Frontend 패키지 선택 (index.html, app.js, style.css)

### Landing Page

```html
<!-- templates/index.html -->
<div id="landing-page" style="display:none;">
    <div class="landing-header">
        <h2>SCODA Desktop</h2>
        <p>Select a package to explore</p>
    </div>
    <div class="package-grid" id="package-grid"></div>
</div>

<div id="viewer-container">  <!-- 기존 view-tree, view-table, view-chart 감싸기 -->
    ...기존 구조...
</div>
```

### app.js 변경

```javascript
// 새 상태
let currentPackage = null;   // 현재 열린 패키지 이름
let apiBase = '';             // '' (legacy) 또는 '/api/pkg/<name>'

// 초기화 변경
document.addEventListener('DOMContentLoaded', async () => {
    genusModal = new bootstrap.Modal(document.getElementById('genusModal'));
    await loadPackages();    // loadManifest() + loadTree() 대신
});

async function loadPackages() {
    const resp = await fetch('/api/packages');
    const packages = await resp.json();

    if (packages.length === 0) {
        // 패키지 없음 → 에러 표시
    } else if (packages.length === 1) {
        // 하나 → 바로 열기
        await openPackage(packages[0].name);
    } else {
        // 여러 개 → landing page 표시
        renderLandingPage(packages);
    }
}

async function openPackage(name) {
    currentPackage = name;
    apiBase = `/api/pkg/${name}`;

    // landing 숨기고 viewer 표시
    document.getElementById('landing-page').style.display = 'none';
    document.getElementById('viewer-container').style.display = '';

    // navbar 제목 업데이트 (패키지 title)
    await loadManifest();   // apiBase 사용
    loadTree();
}
```

### fetch URL 변경 — `apiBase` prefix

모든 범용 SCODA fetch 호출에 `apiBase` 적용:

| 현재 | 변경 |
|------|------|
| `fetch('/api/manifest')` | `` fetch(`${apiBase}/manifest`) `` |
| `` fetch(`/api/queries/${q}/execute`) `` | `` fetch(`${apiBase}/queries/${q}/execute`) `` |
| `` fetch(`/api/annotations/...`) `` | `` fetch(`${apiBase}/annotations/...`) `` |

**변경하지 않는 것**: detail view의 `source` URL (예: `/api/genus/{id}`) — 이건 manifest에 정의된 절대 경로이므로 그대로 사용. trilobase 전용 엔드포인트는 trilobase 패키지에서만 동작.

### Navbar 업데이트

```html
<nav class="navbar navbar-dark bg-dark">
    <div class="container-fluid">
        <span class="navbar-brand mb-0 h1">
            <i class="bi bi-diagram-3"></i> SCODA Desktop
            <span id="pkg-title" class="navbar-pkg-title"></span>
        </span>
        <a id="pkg-back" class="navbar-text text-light" href="#"
           onclick="showLandingPage()" style="display:none;">
            ← Packages
        </a>
    </div>
</nav>
```

### 파일 변경

| 파일 | 변경 |
|------|------|
| `templates/index.html` | landing-page div, viewer-container wrapper, navbar 수정 (+~20줄) |
| `static/js/app.js` | loadPackages, openPackage, renderLandingPage, apiBase prefix (+~80줄) |
| `static/css/style.css` | landing page 카드 스타일 (+~40줄) |

---

## Phase D: GUI 패키지 표시 갱신 (gui.py)

### 최소 변경

패키지 선택은 브라우저 landing page에서 처리하므로, GUI는 **정보 표시만 갱신**:

- `get_scoda_info()` → `get_registry().list_packages()` 사용
- Information 섹션에 발견된 모든 패키지 표시 (기존: trilobase + paleocore 하드코딩)
- 시작 로그에 발견된 패키지 목록 출력

### 파일 변경

| 파일 | 변경 |
|------|------|
| `scripts/gui.py` | registry 기반 정보 표시 (~+20줄, -10줄) |

---

## 변경하지 않는 파일

- `mcp_server.py` — MCP는 기존 `get_db()` 사용 (trilobase 전용, 변경 불필요)
- `scripts/add_scoda_manifest.py` — manifest 내용 변경 없음
- `scripts/create_paleocore.py` — paleocore DB 생성 변경 없음

---

## 테스트 전략

### 기존 202개 테스트 — 변경 없음

`_set_paths_for_testing()`이 registry를 bypass하므로 기존 테스트 전부 통과.

### 신규 테스트

**`TestPackageRegistry`** (~8개):
- `test_scan_finds_scoda_files` — 디렉토리 스캔
- `test_open_package` — 패키지 열기 + DB 연결
- `test_list_packages` — 패키지 목록 반환
- `test_dependency_resolution` — dependency ATTACH with alias
- `test_package_without_deps` — 독립 패키지 (paleocore)
- `test_overlay_per_package` — 패키지별 overlay DB
- `test_legacy_get_db` — 기존 get_db() 하위 호환
- `test_unknown_package_error` — 미존재 패키지 KeyError

**`TestPackagesEndpoint`** (~3개):
- `test_packages_list` — `/api/packages` 반환 구조
- `test_packages_has_name_and_title` — 각 항목 필수 필드

**`TestNamespacedAPI`** (~10개):
- `test_pkg_manifest` — `/api/pkg/trilobase/manifest` == `/api/manifest`
- `test_pkg_queries` — `/api/pkg/trilobase/queries`
- `test_pkg_query_execute` — `/api/pkg/trilobase/queries/genera_list/execute`
- `test_pkg_metadata` — `/api/pkg/trilobase/metadata`
- `test_pkg_provenance` — `/api/pkg/trilobase/provenance`
- `test_pkg_display_intent` — `/api/pkg/trilobase/display-intent`
- `test_pkg_annotations_crud` — namespaced annotation CRUD
- `test_pkg_not_found` — `/api/pkg/nonexistent/manifest` → 404
- `test_pkg_query_not_found` — `/api/pkg/trilobase/queries/nonexistent/execute` → 404

총 예상: 202 기존 + ~21 신규 = ~223개

---

## 검증 방법

1. `pytest test_app.py test_mcp_basic.py test_mcp.py` — 전체 통과
2. **브라우저 수동 테스트**:
   - trilobase.scoda만 있을 때 → 자동으로 trilobase 열림 (기존과 동일)
   - trilobase.scoda + paleocore.scoda → landing page → 선택 → 해당 패키지 UI
   - paleocore.scoda만 있을 때 → 자동으로 paleocore 열림 → 4개 탭
3. `/api/packages` → JSON으로 패키지 목록 확인
4. `/api/pkg/paleocore/manifest` → paleocore manifest 확인

## 구현 순서

```
Phase A → Phase B → Phase C → Phase D
  |          |          |          |
  scoda_     app.py     frontend   gui.py
  package.py routes     HTML/JS    (cosmetic)
```

각 Phase는 독립 커밋 가능. Phase A+B가 핵심, Phase C가 UX, Phase D는 선택.
