# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Start

**새 세션 시작 시 반드시 `docs/HANDOVER.md`를 먼저 읽을 것.** 현재 프로젝트 상태, 진행 중인 작업, 다음 단계가 정리되어 있음.

## Project Overview

Trilobase is a paleontological database project focused on trilobite taxonomy. The goal is to clean, normalize, and import trilobite genus data from Jell & Adrain (2002) into a structured database.

## Repository Structure

```
trilobase/
├── scoda_desktop/                    # SCODA Desktop runtime package
│   ├── __init__.py
│   ├── scoda_package.py              # Core library (DB access, .scoda packages)
│   ├── app.py                        # Flask web server
│   ├── mcp_server.py                 # MCP server (stdio/SSE)
│   ├── gui.py                        # GUI control panel (tkinter)
│   ├── serve.py                      # Server launcher
│   ├── templates/                    # Generic viewer template
│   └── static/                       # Generic viewer assets
├── tests/                            # Test suite (230 tests)
│   ├── conftest.py                   # Shared fixtures
│   ├── test_runtime.py               # Runtime tests (105)
│   ├── test_trilobase.py             # Trilobase domain tests (108)
│   ├── test_mcp.py                   # MCP tests (16)
│   └── test_mcp_basic.py             # MCP basic test (1)
├── data/                             # Source data files
│   ├── trilobite_genus_list.txt      # 최신 버전 (항상 이 파일 수정)
│   ├── trilobite_genus_list_original.txt
│   ├── trilobite_family_list.txt
│   ├── trilobite_nomina_nuda.txt
│   └── adrain2011.txt
├── scripts/                          # 데이터 파이프라인 스크립트
├── spa/                              # Reference SPA (trilobase 전용)
├── examples/                         # Example SPAs
├── devlog/                           # 작업 기록
│   ├── YYYYMMDD_NNN_*.md            # 작업 로그 (숫자 일련번호)
│   ├── YYYYMMDD_PNN_*.md            # 계획(Plan) 문서
│   └── YYYYMMDD_RNN_*.md            # 리뷰(Review) 문서
├── docs/
│   └── HANDOVER.md                   # 인수인계 문서 (필독)
├── ScodaDesktop.spec                 # PyInstaller spec
├── pytest.ini                        # pytest config (testpaths = tests)
└── requirements.txt
```

## Data Format Conventions

### Time Period Codes
- LCAM/MCAM/UCAM = Lower/Middle/Upper Cambrian
- LORD/MORD/UORD = Lower/Middle/Upper Ordovician
- LSIL/USIL = Lower/Upper Silurian
- LDEV/MDEV/UDEV = Lower/Middle/Upper Devonian
- MISS/PENN = Mississippian/Pennsylvanian
- LPERM/PERM/UPERM = Lower/Middle/Upper Permian

### Nomenclature Symbols
- `[j.s.s. of X]` = junior subjective synonym of X
- `[j.o.s. of X]` = junior objective synonym of X
- `[preocc., replaced by X]` = preoccupied, replaced by X
- `fide AUTHOR, YEAR` = according to AUTHOR, YEAR

### Authority Citations
Standard paleontological format: `AUTHOR, YEAR` (e.g., `LIEBERMAN, 1994`)

## Work Convention

- `data/trilobite_genus_list.txt`가 항상 최신 버전
- 각 Phase 완료 시 반드시 git commit
- 중간 과정 파일은 `_단계명.txt` 접미사로 보존
- 작업 기록은 `devlog/YYYYMMDD_일련번호_제목.md` 형식
  - 작업 로그: 숫자 일련번호 (`001`, `002`, ...)
  - 계획(Plan) 문서: `P00` 형식 (`P01`, `P02`, ...)
  - 리뷰(Review) 문서: `R00` 형식 (`R01`, `R02`, ...)

## Phase 완료 시 필수 작업

**매 Phase 완료 후 반드시 아래 3가지를 수행할 것:**

1. **devlog 기록**: `devlog/YYYYMMDD_NNN_phaseNN_제목.md` 작성
   - 작업 내용, 새 테이블/API/파일, 테스트 결과 포함
2. **HANDOVER.md 갱신**: `docs/HANDOVER.md` 업데이트
   - 완료된 작업 목록, 테이블 목록, 파일 구조, 진행 상태 반영
3. **README.md 갱신** (해당 시): 사용자가 알아야 할 새 기능이 있으면 반영

이 3가지를 별도 커밋으로 기록 (코드 커밋과 분리).
