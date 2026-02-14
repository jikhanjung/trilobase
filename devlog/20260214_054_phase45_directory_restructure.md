# Phase 45 완료: 디렉토리 구조 정리 — Runtime/Data 분리

**날짜**: 2026-02-14
**계획 문서**: `devlog/20260214_P39_phase45_directory_restructure.md`

## 개요

SCODA Desktop 런타임(범용 뷰어)과 Trilobase 데이터 파이프라인을 물리적으로 분리.
향후 repo 분할을 준비하는 디렉토리 재구조화.

## 변경 사항

### 1. scoda_desktop/ 패키지 생성
- `scoda_package.py`, `app.py`, `mcp_server.py` → `scoda_desktop/`
- `templates/`, `static/` → `scoda_desktop/`
- `scripts/gui.py`, `scripts/serve.py` → `scoda_desktop/`
- `scripts/build.py`는 `scripts/`에 유지 (빌드 도구는 런타임 아님)
- `scoda_desktop/__init__.py` 신규 생성
- 내부 import: 절대 → 상대 (`from .scoda_package import ...`)
- subprocess 호출: 파일 경로 → `-m` 플래그 (`python -m scoda_desktop.app`)
- `_resolve_paths()`, `get_registry()`: base_dir을 프로젝트 루트로 수정 (한 단계 상위)

### 2. tests/ 디렉토리 생성 + 테스트 분리
- `test_app.py` (213개) → 두 파일로 분리:
  - `tests/test_runtime.py` (105개): SCODA Desktop 범용 테스트 (17 classes)
  - `tests/test_trilobase.py` (108개): Trilobase 도메인 테스트 (14 classes)
- `conftest.py` → `tests/conftest.py` (공유 fixtures + anyio_backend)
- `test_mcp.py`, `test_mcp_basic.py` → `tests/`
- `pytest.ini`: `testpaths = tests` 추가

### 3. data/ 디렉토리 생성
- 13개 소스 데이터 파일 이동 (.txt, .pdf)
- 9개 스크립트의 경로 참조 `data/` prefix 추가

### 4. import 수정 (총 30개 파일)
- scoda_desktop/ 내부 5개: 상대 import
- scripts/ 3개: `scoda_desktop.scoda_package` 절대 import
- tests/ 4개: `scoda_desktop.*` 절대 import + `-m` subprocess args

### 5. ScodaDesktop.spec 갱신
- entry point: `scoda_desktop/gui.py`, `scoda_desktop/mcp_server.py`
- datas: `('scoda_desktop', 'scoda_desktop')` 패키지 전체 포함
- hiddenimports: `scoda_desktop.*` 추가

## 테스트 결과

```
tests/test_mcp.py ................                    [  6%]
tests/test_mcp_basic.py .                             [  7%]
tests/test_runtime.py ...................................  [ 53%]
tests/test_trilobase.py ...............................  [100%]

230 passed in 180s
```

### 6. build.py 리팩토링 — SCODA 패키지 생성 로직 분리
- `create_scoda_package()`, `create_paleocore_scoda_package()` 중복 코드 삭제 (70줄)
- 기존 `create_scoda.py`, `create_paleocore_scoda.py`를 subprocess로 호출 (`--output dist/...`)
- `build.py`에서 `scoda_desktop.scoda_package` import 의존성 제거
- `--no-scoda` 옵션 추가: exe만 빌드하고 .scoda 생성 건너뛰기 가능
- 역할 분리: `build.py` = PyInstaller exe 빌드 전용, `create_*.py` = .scoda 패키지 생성 전용

## 최종 디렉토리 구조

```
trilobase/
├── scoda_desktop/              # Runtime package
│   ├── __init__.py
│   ├── scoda_package.py        # Core library
│   ├── app.py                  # Flask web server
│   ├── mcp_server.py           # MCP server
│   ├── gui.py                  # GUI control panel
│   ├── serve.py                # Server launcher
│   ├── templates/index.html    # Generic viewer
│   └── static/                 # Generic viewer assets
├── tests/                      # Test suite
│   ├── conftest.py             # Shared fixtures
│   ├── test_runtime.py         # Runtime tests (105)
│   ├── test_trilobase.py       # Trilobase tests (108)
│   ├── test_mcp.py             # MCP tests (16)
│   └── test_mcp_basic.py       # MCP basic test (1)
├── data/                       # Source data files
│   ├── trilobite_genus_list.txt
│   ├── trilobite_family_list.txt
│   ├── adrain2011.txt
│   └── ... (13 files total)
├── spa/                        # Reference SPA (stays)
├── scripts/                    # Data pipeline + build scripts
│   ├── build.py                # PyInstaller exe 빌드 전용
│   ├── create_scoda.py         # trilobase.scoda 생성
│   ├── create_paleocore_scoda.py  # paleocore.scoda 생성
│   └── ... (24 scripts total)
├── ScodaDesktop.spec           # PyInstaller spec (updated)
├── pytest.ini                  # testpaths = tests
└── ... (DB, docs, devlog, vendor, examples)
```
