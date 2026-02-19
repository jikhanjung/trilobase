# 068: Page-Level Back Navigation + 서빙 경로 수정

**날짜:** 2026-02-16

## 목표

SPA에서 탭 전환 및 트리 Family 선택 시 이전 상태로 돌아갈 수 있는 back navigation 구현. 기존에는 모달 내 detail 간 back만 있었음 (`detailHistory`).

## 구현 내용

### 1. `navHistory` 스택 (page-level back)

- `navHistory` 배열: 탭 전환 / Family 선택 시 이전 상태를 push
- `captureNavState()`: 현재 상태 캡처 (view, familyId, familyName, tableSort, tableSearch, showOnlyValid)
- `navGoBack()`: 스택에서 pop하여 이전 상태 복원
- `updateNavBackButton()`: `#navBackBtn` 표시/숨김 토글
- `_suppressNavHistory`: navGoBack 실행 중 재귀 push 방지 플래그

### 2. `switchToView()` 수정

- 탭 전환 시 현재 상태를 `navHistory`에 push (동일 탭이면 skip)

### 3. `selectTreeLeaf()` 수정

- Family 선택 시 `navHistory`에 push (첫 선택 포함 — "선택 없음" 상태로 복원 가능)
- `selectedFamilyName` 변수 추가

### 4. `detailHistory` 스택 (modal back) — generic viewer에 추가

- generic viewer (`app.js`)에는 detail back navigation이 없었음
- `detailHistory`, `currentDetail`, `detailGoBack()`, `updateDetailBackButton()` 추가
- `openDetail()`에서 이전 detail을 push하도록 수정

### 5. Back 버튼 UI

- **탭 바**: `#navBackBtn` (← 아이콘, 스택 비면 `d-none`)
- **모달 헤더**: `#detailBackBtn` (← 아이콘, 스택 비면 `d-none`)

### 6. Alt+← 키보드 단축키

- 모달 열림 + `detailHistory` 있으면 → detail back
- 모달 닫힘 + `navHistory` 있으면 → page-level back

### 7. CSS

- `.view-tabs-bar` wrapper 스타일 (back 버튼 + 탭 바 flex 레이아웃)
- `.nav-back-btn` 스타일

## 서빙 경로 문제 발견 및 수정

### 문제 1: 개발 모드에서 Reference SPA 미서빙

**증상:** `python -m scoda_desktop.serve --package trilobase` 실행 시 generic viewer("SCODA Desktop")가 서빙됨. Reference SPA("Trilobase")가 아님.

**원인:** `_get_reference_spa_dir()`가 `.scoda` 패키지에서 추출된 SPA 디렉토리(`trilobase_spa/`)만 탐색. 개발 모드에서는 `.scoda` 없이 `.db`를 직접 사용하므로 항상 `None` 반환 → generic viewer 폴백.

**수정:** 개발 모드(`frozen=False`) fallback 추가 — 프로젝트 루트의 `spa/` 디렉토리를 직접 서빙.

### 문제 2: Generic viewer의 static 파일 404

**증상:** Generic viewer HTML은 서빙되지만 `/static/js/app.js`, `/static/css/style.css`가 404.

**원인:** `app.py`에 `StaticFiles` mount가 없었음. `/{filename:path}` catch-all 라우트는 extracted SPA 디렉토리에서만 파일을 찾음.

**수정:** `app.mount("/static", StaticFiles(...))` 추가.

### 문제 3: EXE frozen 모드에서 `_MEIPASS/spa/` 미탐색

**증상:** EXE 실행 시 console.log도 안 나옴 — JS 자체가 로딩되지 않음.

**원인:** `ScodaDesktop.spec`에 `('spa', 'spa')` datas가 있어서 `_MEIPASS/spa/`에 SPA 파일이 번들됨. 하지만 `_get_reference_spa_dir()`는 frozen 모드에서 `_MEIPASS`를 전혀 안 봤음. extracted SPA(`trilobase_spa/`) 없으면 → generic viewer 서빙 → static 404 (StaticFiles mount는 이번에 추가했으나 `_MEIPASS` 경로 문제는 별도).

**수정:** frozen 모드 fallback 추가 — `sys._MEIPASS/spa/` 디렉토리 탐색.

### `_get_reference_spa_dir()` 최종 탐색 순서

```
1. Extracted SPA: {scan_dir}/trilobase_spa/  (Extract SPA 버튼으로 추출)
2. Bundled SPA:   sys._MEIPASS/spa/          (PyInstaller 번들, frozen 전용)
3. Source SPA:    {project_root}/spa/         (개발 모드 전용)
```

## 수정 파일

| 파일 | 변경 내용 |
|------|----------|
| `spa/index.html` | navHistory 스택, captureNavState, navGoBack, updateNavBackButton, switchToView/selectTreeLeaf 수정, navBackBtn HTML, nav-back-btn CSS, Alt+← 수정, console.log 디버깅 |
| `scoda_desktop/static/js/app.js` | 위와 동일 + detailHistory/detailGoBack/updateDetailBackButton 추가 (기존에 없었음), console.log 디버깅 |
| `scoda_desktop/static/css/style.css` | `.view-tabs-bar` wrapper, `.nav-back-btn` 스타일, 높이 계산 셀렉터 변경 |
| `scoda_desktop/templates/index.html` | `view-tabs-bar` wrapper + `navBackBtn` 추가, `detailBackBtn` 모달 헤더에 추가 |
| `scoda_desktop/app.py` | `import sys` 추가, `StaticFiles` mount 추가, `_get_reference_spa_dir()` 3단계 fallback |
| `tests/test_runtime.py` | generic viewer 테스트 2개에 `monkeypatch`로 dev fallback 비활성화 |

## 테스트

- 229개 전부 통과
- EXE 빌드 후 테스트 필요 (frozen 모드 `_MEIPASS/spa/` 경로 확인)

## 현재 상태: 미동작

EXE 빌드 후 테스트 결과 **back navigation 버튼이 여전히 보이지 않음**. console.log도 출력되지 않아 JS 코드 자체가 실행되지 않는 것으로 추정.

가능한 원인:
- EXE 빌드 시 소스 파일 변경사항이 반영되지 않았을 가능성 (빌드 캐시)
- `_MEIPASS/spa/` fallback이 실제 frozen 환경에서 동작하는지 미확인
- `StaticFiles` mount 순서와 catch-all `/{filename:path}` 라우트 간 충돌 가능성
- `.scoda` ZIP 안의 SPA가 옛날 버전일 가능성 (Extract SPA 시)

## 결론: 전체 롤백

위 모든 수정에도 불구하고 EXE에서 back navigation이 동작하지 않음. console.log조차 출력되지 않아 근본적으로 수정된 JS가 브라우저에 도달하지 않는 것으로 판단.

**모든 변경사항을 마지막 commit 상태로 되돌리고, navigation 관련 코드가 전혀 없는 상태에서 처음부터 다시 시작하기로 결정.**

롤백 대상 파일:
- `spa/index.html`
- `scoda_desktop/static/js/app.js`
- `scoda_desktop/static/css/style.css`
- `scoda_desktop/templates/index.html`
- `scoda_desktop/app.py`
- `tests/test_runtime.py`
