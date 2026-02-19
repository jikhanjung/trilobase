# P62: ScodaEngine / Trilobase 프로젝트 분리 계획

**날짜**: 2026-02-19
**상태**: 계획 수립 완료

## 배경

Phase 46에서 runtime의 도메인 코드를 완전히 제거했으나, 여전히 하나의 git repo에 있어 웹 UI 수정 시 ScodaEngine 이슈인지 Trilobase 이슈인지 혼선이 발생. 두 프로젝트를 별도 repo로 분리하여 독립 개발·배포.

## 핵심 결정사항

- **패키지명**: `scoda_desktop` → `scoda_engine` (pip name: `scoda-engine`)
- **새 repo 경로**: `/mnt/d/projects/scoda-engine`
- **의존성**: Trilobase는 `pip install scoda-engine`으로 참조
- **apt 배포**: 향후 목표 (pip 패키지 선행)

---

## 구현 단계

### Step 1: scoda-engine repo 초기화

```bash
mkdir /mnt/d/projects/scoda-engine && cd /mnt/d/projects/scoda-engine && git init
```

### Step 2: 파일 복사 + 디렉토리 리네이밍

trilobase에서 scoda-engine으로 복사 (git history는 보존하지 않음):

| From (trilobase/) | To (scoda-engine/) | 비고 |
|---|---|---|
| `scoda_desktop/` | `scoda_engine/` | **디렉토리명 변경** |
| `tests/test_runtime.py` | `tests/test_runtime.py` | 122개 runtime 테스트 |
| `tests/test_mcp.py` | `tests/test_mcp.py` | 16개 MCP 테스트 |
| `tests/test_mcp_basic.py` | `tests/test_mcp_basic.py` | 1개 기본 테스트 |
| `tests/conftest.py` | `tests/conftest.py` | 그대로 복사 후 import만 변경 |
| `scripts/build.py` | `scripts/build.py` | trilobase 참조 제거 |
| `scripts/validate_manifest.py` | `scripts/validate_manifest.py` | 변경 없음 |
| `scripts/init_overlay_db.py` | `scripts/init_overlay_db.py` | 변경 없음 |
| `scripts/release.py` | `scripts/release.py` | 범용화 |
| `ScodaDesktop.spec` | `ScodaDesktop.spec` | import 경로 변경 |
| `launcher_gui.py` | `launcher_gui.py` | import 경로 변경 |
| `launcher_mcp.py` | `launcher_mcp.py` | import 경로 변경 |
| `examples/genus-explorer/` | `examples/genus-explorer/` | 변경 없음 |
| `pytest.ini` | `pytest.ini` | 변경 없음 |

### Step 3: import 경로 일괄 치환

모든 파일에서 `scoda_desktop` → `scoda_engine`:
- `scoda_engine/*.py` — 내부 상대 import는 변경 불필요, docstring/comment만
- `tests/*.py` — import 문 치환
- `scripts/*.py`, `launcher_*.py`, `ScodaDesktop.spec` — import 경로 치환

### Step 4: conftest.py 처리 (실용적 접근)

현재 conftest.py의 테스트 데이터는 trilobase 테마이지만, runtime 테스트가 검증하는 것은 SCODA 메커니즘이므로 테스트 데이터 자체는 무관.
→ **conftest.py를 그대로 복사하고 import만 변경.** 모든 테스트가 즉시 통과. generic fixture는 후속 작업.

### Step 5: scripts/build.py 범용화

- `create_scoda_packages()` 함수 삭제
- `--no-scoda` 플래그 삭제
- `print_results()`에서 trilobase/paleocore 참조 제거
- EXE 빌드 기능만 유지

### Step 6: pyproject.toml 생성

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "scoda-engine"
version = "0.1.0"
description = "SCODA Engine — runtime for Self-Contained Data Artifacts"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.104.0", "httpx>=0.25.0", "mcp>=1.0.0",
    "starlette>=0.27.0", "uvicorn>=0.24.0", "jinja2>=3.1.0",
]

[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-asyncio>=0.21", "pyinstaller>=5.0"]

[project.scripts]
scoda-serve = "scoda_engine.serve:main"
scoda-mcp = "scoda_engine.mcp_server:main"

[tool.setuptools.packages.find]
include = ["scoda_engine*"]

[tool.setuptools.package-data]
scoda_engine = ["templates/*.html", "static/**/*"]
```

### Step 7: docs 복사

scoda-engine으로 이동: API_REFERENCE.md, MCP_GUIDE.md, RELEASE_GUIDE.md, SCODA_CONCEPT.md, SCODA_WHITEPAPER.md, SCODA_Stable_UID_Schema_v0.2.md
trilobase에 잔류: HANDOFF.md, paleocore_schema.md

### Step 8: README.md, .gitignore, CLAUDE.md 생성

### Step 9: scoda-engine 검증 + 커밋

```bash
pip install -e ".[dev]" && pytest tests/
```

### Step 10: trilobase repo 정리

삭제: scoda_desktop/, 이동된 tests/scripts/docs, ScodaDesktop.spec, launcher_*.py, examples/

### Step 11: trilobase import 경로 갱신

`scoda_desktop` → `scoda_engine`: conftest.py, test_trilobase.py, create_scoda.py, create_paleocore_scoda.py

### Step 12: trilobase requirements.txt 갱신

```
-e /mnt/d/projects/scoda-engine[dev]
```

### Step 13: trilobase 검증 + 커밋

```bash
pip install -e /mnt/d/projects/scoda-engine[dev] && pytest tests/
```

### Step 14: CLAUDE.md, HANDOFF.md 갱신

---

## 분리 후 최종 구조

### scoda-engine/
```
scoda-engine/
├── pyproject.toml
├── README.md, CLAUDE.md, .gitignore, pytest.ini
├── ScodaDesktop.spec, launcher_gui.py, launcher_mcp.py
├── scoda_engine/           ← renamed from scoda_desktop
│   ├── __init__.py, scoda_package.py, app.py, mcp_server.py
│   ├── gui.py, serve.py
│   ├── templates/index.html
│   └── static/{css,js}/
├── scripts/                ← build.py, validate_manifest.py, init_overlay_db.py, release.py
├── examples/genus-explorer/
├── tests/                  ← conftest.py, test_runtime(122), test_mcp(16), test_mcp_basic(1)
└── docs/                   ← SCODA 관련 문서
```

### trilobase/ (정리 후)
```
trilobase/
├── CLAUDE.md, pytest.ini, requirements.txt (scoda-engine 의존)
├── trilobase.db, paleocore.db
├── data/, spa/, vendor/, devlog/
├── scripts/                ← 도메인 스크립트만 (22개)
├── tests/                  ← conftest.py, test_trilobase.py (123)
└── docs/                   ← HANDOFF.md, paleocore_schema.md
```

## 검증 체크리스트

- [ ] scoda-engine: `pip install -e ".[dev]"` 성공
- [ ] scoda-engine: `pytest tests/` 139개 통과
- [ ] scoda-engine: `python -m scoda_engine.serve` 서버 시작
- [ ] scoda-engine: `python -m scoda_engine.mcp_server` MCP 시작
- [ ] trilobase: `pytest tests/` 123개 통과
- [ ] trilobase: `python scripts/create_scoda.py --dry-run` 정상
- [ ] 웹 뷰어에서 trilobase.scoda 로딩 정상

## 후속 작업

- scoda-engine conftest.py → generic test fixture 전환 (trilobase 테마 제거)
- PyPI 배포
- apt 패키지 생성 (stdeb 또는 fpm)
