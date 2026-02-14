# Phase 45: 디렉토리 구조 정리 — Runtime/Data 분리

**날짜**: 2026-02-14
**상태**: 계획

## Context

SCODA Desktop 런타임(범용 뷰어)과 Trilobase 데이터 파이프라인이 하나의 flat 구조에 혼재.
Phase 44에서 generic viewer와 reference SPA를 분리한 것에 이어, 디렉토리 수준에서
런타임과 도메인 데이터를 물리적으로 분리하여 향후 repo 분할을 준비.

## 목표 디렉토리 구조

```
trilobase/
├── scoda_desktop/                  # ← Runtime package (향후 별도 repo)
│   ├── __init__.py                 #   패키지 init
│   ├── scoda_package.py            #   Core library (from root)
│   ├── app.py                      #   Flask web server (from root)
│   ├── mcp_server.py               #   MCP server (from root)
│   ├── gui.py                      #   GUI control panel (from scripts/)
│   ├── serve.py                    #   Server launcher (from scripts/)
│   ├── build.py                    #   PyInstaller build (from scripts/)
│   ├── templates/                  #   Generic viewer template (from root)
│   │   └── index.html
│   └── static/                     #   Generic viewer assets (from root)
│       ├── css/style.css
│       └── js/app.js
│
├── tests/                          # ← Tests (from root, runtime/trilobase 분리)
│   ├── conftest.py                 #   공유 fixtures (canonical_db 등)
│   ├── test_runtime.py             #   Runtime 테스트 (17 classes, ~100개)
│   ├── test_trilobase.py           #   Trilobase 테스트 (14 classes, ~113개)
│   ├── test_mcp.py                 #   MCP 테스트 (trilobase 전용, 16개)
│   └── test_mcp_basic.py           #   MCP 기본 테스트 (1개)
│
├── data/                           # ← Source data files (from root)
│   ├── trilobite_genus_list.txt    #   Primary genus list
│   ├── trilobite_genus_list_original.txt
│   ├── trilobite_genus_list_*.txt  #   Intermediate versions
│   ├── trilobite_family_list.txt
│   ├── trilobite_nomina_nuda.txt
│   ├── adrain2011.txt
│   ├── Jell_and_Adrain_2002_Literature_Cited.txt
│   ├── unlinked_*.txt              #   Diagnostic outputs
│   └── *.pdf                       #   Reference PDFs
│
├── ScodaDesktop.spec               #   PyInstaller spec (stays, 경로만 갱신)
├── pytest.ini                      #   testpaths = tests 추가
├── requirements.txt
├── CLAUDE.md
│
├── spa/                            #   Reference SPA (trilobase 전용, stays)
├── examples/                       #   Example SPAs (stays)
├── scripts/                        #   Data pipeline + packaging only (stays)
│   ├── create_scoda.py
│   ├── create_paleocore*.py
│   ├── release.py
│   ├── create_database.py
│   ├── normalize_*.py
│   ├── import_*.py
│   └── ... (24개 데이터 스크립트)
│
├── trilobase.db, paleocore.db      #   DB files (stays at root)
├── *.scoda                         #   Packages (stays at root)
├── vendor/                         #   External vendor data (stays)
├── docs/                           #   Documentation (stays)
└── devlog/                         #   Work logs (stays)
```

## Import 전략

### scoda_desktop/ 내부: 상대 import
```python
# app.py
from .scoda_package import get_db, get_registry, ...

# gui.py
from . import scoda_package
from .app import app  # frozen mode
```

### 외부 (scripts/, tests/): 절대 import
```python
# scripts/create_scoda.py (기존 sys.path hack 유지)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from scoda_desktop.scoda_package import ScodaPackage, _sha256_file

# tests/test_runtime.py
from scoda_desktop.app import app
from scoda_desktop.scoda_package import get_db, ScodaPackage
```

### subprocess 실행: `-m` 플래그
```python
# gui.py dev mode
subprocess.Popen([python_exe, '-m', 'scoda_desktop.app', '--package', ...])
subprocess.Popen([python_exe, '-m', 'scoda_desktop.mcp_server', '--mode', 'sse', ...])

# test_mcp*.py
StdioServerParameters(command="python3", args=["-m", "scoda_desktop.mcp_server"])
```

## 구현 단계

### Step 1: scoda_desktop/ 패키지 생성 + git mv
- `mkdir scoda_desktop`
- `__init__.py` 생성 (빈 파일 또는 최소 export)
- `git mv` 8개 파일/디렉토리:
  - `scoda_package.py` → `scoda_desktop/`
  - `app.py` → `scoda_desktop/`
  - `mcp_server.py` → `scoda_desktop/`
  - `templates/` → `scoda_desktop/templates/`
  - `static/` → `scoda_desktop/static/`
  - `scripts/gui.py` → `scoda_desktop/gui.py`
  - `scripts/serve.py` → `scoda_desktop/serve.py`
  - `scripts/build.py` → `scoda_desktop/build.py`

### Step 2: tests/ 디렉토리 생성 + 테스트 분리
- `mkdir tests`
- `git mv conftest.py tests/`
- `git mv test_mcp.py tests/`
- `git mv test_mcp_basic.py tests/`
- `test_app.py`를 **두 파일로 분리**:
  - `tests/test_runtime.py` — Runtime 테스트 (17 classes)
  - `tests/test_trilobase.py` — Trilobase 테스트 (14 classes)
- `git rm test_app.py` (원본 삭제)
- `pytest.ini`에 `testpaths = tests` 추가

**Runtime 테스트 (test_runtime.py)** — SCODA Desktop 범용:
- `TestCORS`, `TestIndex`, `TestFlaskAutoSwitch`, `TestGenericViewerFallback`
- `TestScodaPackage`, `TestPackageRegistry`, `TestActivePackage`, `TestScodaPackageSPA`
- `TestGenericDetailEndpoint`
- `TestApiMetadata`, `TestApiProvenance`, `TestApiDisplayIntent`
- `TestApiQueries`, `TestApiQueryExecute`, `TestApiManifest`
- `TestAnnotations`, `TestRelease`

**Trilobase 테스트 (test_trilobase.py)** — 도메인 전용:
- `TestApiTree`, `TestApiFamilyGenera`, `TestApiRankDetail`, `TestApiGenusDetail`
- `TestApiCountryDetail`, `TestApiRegionDetail`, `TestApiChronostratDetail`
- `TestGenusDetailICSMapping`, `TestICSChronostrat`
- `TestPaleocoreScoda`, `TestCombinedScodaDeployment`, `TestApiPaleocoreStatus`
- `TestManifestDetailSchema`, `TestManifestTreeChart`

공유 fixture(`canonical_db` 등)는 `tests/conftest.py`에 유지.

### Step 3: data/ 디렉토리 생성 + 소스 파일 이동
- `mkdir data`
- `git mv` 대상 파일들:
  - `trilobite_genus_list.txt` → `data/`
  - `trilobite_genus_list_original.txt` → `data/`
  - `trilobite_genus_list_characters_fixed.txt` → `data/`
  - `trilobite_genus_list_structure_fixed.txt` → `data/`
  - `trilobite_family_list.txt` → `data/`
  - `trilobite_nomina_nuda.txt` → `data/`
  - `adrain2011.txt` → `data/`
  - `Jell_and_Adrain_2002_Literature_Cited.txt` → `data/`
  - `unlinked_synonyms.txt` → `data/`
  - `unlinked_taxa_no_formation.txt` → `data/`
  - `unlinked_taxa_no_location.txt` → `data/`
  - `AVAILABLE_GENERIC_NAMES_FOR_TRILOBITES.pdf` → `data/`
  - `Adrain - 2011 - *.pdf` → `data/`
- NOT moved: `requirements.txt` (프로젝트 설정 파일)

**scripts/ 경로 수정** (~9개 파일):
- `scripts/create_database.py`: `'trilobite_genus_list.txt'` → `'data/trilobite_genus_list.txt'`
- `scripts/normalize_lines.py`: 입출력 경로에 `data/` prefix
- `scripts/normalize_families.py`: `'trilobite_family_list.txt'` → `'data/trilobite_family_list.txt'`
- `scripts/extract_families.py`: `'trilobite_genus_list.txt'` → `'data/trilobite_genus_list.txt'`
- `scripts/parse_references.py`: `Jell_and_Adrain_2002_Literature_Cited.txt` → `data/` prefix
- `scripts/populate_taxonomic_ranks.py`: `'adrain2011.txt'` → `'data/adrain2011.txt'`
- `scripts/check_balance.py`, `check_duplicates.py`: path prefix
- `scripts/add_new_families.py`: `'trilobite_family_list.txt'` → `'data/trilobite_family_list.txt'`
- `scripts/find_bad_semicolons.py`: path prefix

### Step 4: scoda_desktop/ 내부 import 수정

**`scoda_desktop/app.py`:**
- `from scoda_package import ...` → `from .scoda_package import ...`
- `__main__` 블록의 `from scoda_package import` → `from .scoda_package import`

**`scoda_desktop/mcp_server.py`:**
- `from scoda_package import ...` → `from .scoda_package import ...`

**`scoda_desktop/gui.py`:**
- sys.path hack 삭제
- `import scoda_package` → `from . import scoda_package`
- `from app import app` → `from .app import app`
- subprocess: `[python_exe, app_py, ...]` → `[python_exe, '-m', 'scoda_desktop.app', ...]`
- subprocess: `[python_exe, mcp_py, ...]` → `[python_exe, '-m', 'scoda_desktop.mcp_server', ...]`
- `mcp_py`/`app_py` 변수 제거

**`scoda_desktop/serve.py`:**
- `from scoda_package import ...` → `from .scoda_package import ...`
- `from app import app` → `from .app import app`
- base_path 계산 수정

**`scoda_desktop/build.py`:**
- `from scoda_package import ...` → `from .scoda_package import ...`

### Step 5: 외부 import 수정

**`scripts/create_scoda.py`:**
- `from scoda_package import ...` → `from scoda_desktop.scoda_package import ...`

**`scripts/create_paleocore_scoda.py`:**
- `from scoda_package import ...` → `from scoda_desktop.scoda_package import ...`

**`scripts/release.py`:**
- `from scoda_package import ...` → `from scoda_desktop.scoda_package import ...`

### Step 6: 테스트 import 수정

**`tests/test_runtime.py`** + **`tests/test_trilobase.py`** (양쪽 모두):
- `import scoda_package` → `import scoda_desktop.scoda_package as scoda_package`
- `from app import app` → `from scoda_desktop.app import app`
- `from scoda_package import get_db, ScodaPackage` → `from scoda_desktop.scoda_package import get_db, ScodaPackage`
- `from scoda_package import PackageRegistry` → `from scoda_desktop.scoda_package import PackageRegistry`
- `import scoda_package as sp` → `import scoda_desktop.scoda_package as sp`

**`tests/test_mcp.py`:**
- subprocess args: `["mcp_server.py"]` → `["-m", "scoda_desktop.mcp_server"]`

**`tests/test_mcp_basic.py`:**
- subprocess args: `["mcp_server.py"]` → `["-m", "scoda_desktop.mcp_server"]`

### Step 7: ScodaDesktop.spec 갱신

GUI exe Analysis:
```python
Analysis(
    ['scoda_desktop/gui.py'],
    datas=[
        ('scoda_desktop', 'scoda_desktop'),
        ('spa', 'spa'),
    ],
    hiddenimports=[
        'scoda_desktop',
        'scoda_desktop.scoda_package',
        'scoda_desktop.app',
        'flask', 'uvicorn', ...
    ],
)
```

MCP exe Analysis:
```python
Analysis(
    ['scoda_desktop/mcp_server.py'],
    datas=[
        ('scoda_desktop/scoda_package.py', 'scoda_desktop'),
        ('scoda_desktop/__init__.py', 'scoda_desktop'),
    ],
    ...
)
```

### Step 8: 문서 갱신
- devlog 작성
- `docs/HANDOVER.md`: 파일 구조 섹션 갱신
- `CLAUDE.md`: Repository Structure 갱신

### Step 9: 테스트 실행 + 검증
```bash
pytest tests/
```
230개 전부 통과 확인.

## 주요 파일별 변경 요약

| 파일 | 변경 내용 |
|------|----------|
| `scoda_desktop/__init__.py` | 신규 |
| `scoda_desktop/app.py` | import 2곳 |
| `scoda_desktop/mcp_server.py` | import 1곳 |
| `scoda_desktop/gui.py` | import 3곳 + subprocess 2곳 + sys.path 제거 |
| `scoda_desktop/serve.py` | import 2곳 + base_path |
| `scoda_desktop/build.py` | import 2곳 |
| `scripts/create_scoda.py` | import 1곳 + data path |
| `scripts/create_paleocore_scoda.py` | import 1곳 |
| `scripts/release.py` | import 1곳 |
| `scripts/create_database.py` | data/ path prefix |
| `scripts/normalize_*.py` | data/ path prefix |
| `scripts/populate_taxonomic_ranks.py` | data/ path prefix |
| `scripts/parse_references.py` | data/ path prefix |
| `scripts/extract_families.py` | data/ path prefix |
| `scripts/add_new_families.py` | data/ path prefix |
| `scripts/check_*.py` | data/ path prefix |
| `scripts/find_bad_semicolons.py` | data/ path prefix |
| `tests/test_runtime.py` | 신규 (test_app.py에서 17 classes 분리 + import 수정) |
| `tests/test_trilobase.py` | 신규 (test_app.py에서 14 classes 분리 + import 수정) |
| `tests/test_mcp.py` | subprocess args 1곳 |
| `tests/test_mcp_basic.py` | subprocess args 1곳 |
| `ScodaDesktop.spec` | entry point + datas 전면 갱신 |
| `pytest.ini` | testpaths 추가 |
| `CLAUDE.md` | Repository Structure 갱신 |
| `GEMINI.md` | Repository Structure 갱신 |
| `docs/HANDOVER.md` | 파일 구조 섹션 갱신 |

## 검증 방법

1. `pytest tests/` — 230개 전부 통과
2. `python -m scoda_desktop.app --package trilobase` — Flask 서버 정상 시작
3. `python -m scoda_desktop.serve --package trilobase` — 브라우저 자동 오픈
4. `python scripts/create_scoda.py --dry-run` — 패키징 스크립트 정상
