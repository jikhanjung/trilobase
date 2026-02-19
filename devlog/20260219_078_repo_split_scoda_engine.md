# ScodaEngine / Trilobase 프로젝트 분리

**날짜:** 2026-02-19
**계획 문서:** `devlog/20260219_P62_repo_split_scoda_engine.md`

## 개요

Phase 46에서 runtime의 도메인 코드를 완전히 제거했으나, 여전히 하나의 git repo에 있어 개발 혼선 발생. SCODA Engine 런타임을 별도 repo로 분리.

## 변경 사항

### 1. scoda-engine 새 repo 생성 (`/mnt/d/projects/scoda-engine`)

| 구분 | 내용 |
|------|------|
| 패키지명 | `scoda_desktop` → `scoda_engine` |
| pip name | `scoda-engine` |
| 경로 | `/mnt/d/projects/scoda-engine` |

### 2. 이동된 파일

| From (trilobase/) | To (scoda-engine/) |
|---|---|
| `scoda_desktop/` | `scoda_engine/` (디렉토리명 변경) |
| `tests/test_runtime.py` | `tests/test_runtime.py` |
| `tests/test_mcp.py` | `tests/test_mcp.py` |
| `tests/test_mcp_basic.py` | `tests/test_mcp_basic.py` |
| `tests/conftest.py` | `tests/conftest.py` (import만 변경) |
| `scripts/build.py` | `scripts/build.py` (범용화) |
| `scripts/validate_manifest.py` | `scripts/validate_manifest.py` |
| `scripts/init_overlay_db.py` | `scripts/init_overlay_db.py` |
| `scripts/release.py` | `scripts/release.py` |
| `ScodaDesktop.spec` | `ScodaDesktop.spec` |
| `launcher_gui.py` | `launcher_gui.py` |
| `launcher_mcp.py` | `launcher_mcp.py` |
| `examples/` | `examples/` |
| `pytest.ini` | `pytest.ini` |
| `docs/API_REFERENCE.md` | `docs/API_REFERENCE.md` |
| `docs/MCP_GUIDE.md` | `docs/MCP_GUIDE.md` |
| `docs/RELEASE_GUIDE.md` | `docs/RELEASE_GUIDE.md` |
| `docs/SCODA_CONCEPT.md` | `docs/SCODA_CONCEPT.md` |
| `docs/SCODA_WHITEPAPER.md` | `docs/SCODA_WHITEPAPER.md` |
| `docs/SCODA_Stable_UID_Schema_v0.2.md` | `docs/SCODA_Stable_UID_Schema_v0.2.md` |
| `docs/SCODA_Concept_and_Architecture_Summary.md` | `docs/SCODA_Concept_and_Architecture_Summary.md` |

### 3. scoda-engine 신규 파일

- `pyproject.toml`: setuptools 기반 패키지 설정, `pip install -e ".[dev]"`
- `README.md`: 프로젝트 소개, 설치법, 사용법
- `CLAUDE.md`: scoda-engine 전용 Claude Code 지침
- `.gitignore`: Python/PyInstaller/SCODA 패키지 무시

### 4. trilobase import 경로 갱신

| 파일 | 변경 |
|------|------|
| `tests/conftest.py` | `scoda_desktop` → `scoda_engine`, `create_overlay_db` 인라인 |
| `tests/test_trilobase.py` | `scoda_desktop` → `scoda_engine` |
| `scripts/create_scoda.py` | `scoda_desktop` → `scoda_engine` |
| `scripts/create_paleocore_scoda.py` | `scoda_desktop` → `scoda_engine` |

### 5. build.py 범용화

- `create_scoda_packages()` 함수 삭제 (trilobase/paleocore 참조)
- `--no-scoda` 플래그 삭제
- EXE 빌드 기능만 유지

### 6. requirements.txt 갱신

```
-e /mnt/d/projects/scoda-engine[dev]
```

## 테스트 결과

### scoda-engine
- 191 passed, 5 failed (test_mcp.py subprocess tests — CWD에 .scoda 필요)
- test_runtime.py: 122 passed
- test_mcp_basic.py: 1 passed
- test_mcp.py: 1 passed (test_list_tools), 5 failed (데이터 의존)

### trilobase
- 66 passed
- test_trilobase.py: 66 passed

## 삭제된 파일 (trilobase에서)

- `scoda_desktop/` 전체
- `tests/test_runtime.py`, `tests/test_mcp.py`, `tests/test_mcp_basic.py`
- `scripts/build.py`, `scripts/release.py`, `scripts/init_overlay_db.py`
- `ScodaDesktop.spec`, `launcher_gui.py`, `launcher_mcp.py`
- `examples/`
- `docs/API_REFERENCE.md`, `docs/MCP_GUIDE.md`, `docs/RELEASE_GUIDE.md`
- `docs/SCODA_CONCEPT.md`, `docs/SCODA_WHITEPAPER.md`, `docs/SCODA_Stable_UID_Schema_v0.2.md`
- `docs/SCODA_Concept_and_Architecture_Summary.md`

## 후속 작업

- scoda-engine test_mcp.py: CWD에 .scoda 없이도 동작하도록 fixture 개선
- scoda-engine PyPI 배포 준비
- trilobase에서 validate_manifest.py 중복 제거 (scoda_engine 패키지에서 import)
