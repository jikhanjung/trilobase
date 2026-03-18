# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Start

**새 세션 시작 시 반드시 `HANDOFF.md`를 먼저 읽을 것.** 현재 프로젝트 상태, 진행 중인 작업, 다음 단계가 정리되어 있음.

## Project Overview

Trilobase is a paleontological database project. Started with trilobite taxonomy (Jell & Adrain 2002), now expanded to 11 invertebrate phyla via Treatise on Invertebrate Paleontology source data.

**Runtime engine** (`scoda-engine`) is in a separate repository at `/mnt/d/projects/scoda-engine`. This repo contains only trilobase domain data, scripts, and tests.

## Repository Structure

```
trilobase/
├── CLAUDE.md
├── pytest.ini                        # pytest config (testpaths = tests)
├── requirements.txt                  # scoda-engine dependency
├── db/                               # Databases (git tracked, versioned filenames)
│   ├── trilobita-0.3.4.db           # ★ 메인 DB (assertion-centric)
│   ├── brachiopoda-0.2.7.db        # Brachiopod DB (Treatise 1965 & 2000-2006)
│   ├── graptolithina-0.1.3.db      # Graptolite DB (Treatise 1955/1970/2023)
│   ├── chelicerata-0.1.3.db        # Chelicerate DB (Treatise 1955, Part P)
│   ├── ostracoda-0.1.3.db          # Ostracod DB (Treatise 1961, Part Q)
│   ├── bryozoa-0.1.0.db            # Bryozoa DB (Treatise 1953/1983, Part G)
│   ├── coelenterata-0.1.0.db       # Coelenterata DB (Treatise 1956, Part F)
│   ├── hexapoda-0.1.0.db           # Hexapoda DB (Treatise 1992, Part R)
│   ├── porifera-0.1.0.db           # Porifera DB (Treatise 1955-2015, Part E)
│   ├── echinodermata-0.1.0.db      # Echinodermata DB (Treatise 1966-2011, Parts S/T/U)
│   ├── mollusca-0.1.0.db           # Mollusca DB (Treatise 1957-1996, Parts I/K/L/N)
│   ├── paleocore-0.1.4.db          # PaleoCore reference DB
│   └── trilobita-canonical-0.2.6.db # Legacy canonical DB (보존용)
├── dist/                             # Generated artifacts (gitignored)
│   ├── {package}-{ver}.scoda        # 11 taxonomy + paleocore + paleobase .scoda
│   └── *_overlay.db                 # Overlay databases
├── data/                             # Source data files
│   ├── sources/                     # ★ taxonomic source files (*.txt)
│   ├── trilobite_genus_list.txt     # Cleaned genus list (canonical version)
│   ├── trilobite_family_list.txt
│   ├── adrain2011.txt
│   └── mcp_tools_trilobase.json     # MCP 도구 정의
├── scripts/                          # ★ 활성 빌드 스크립트만
│   ├── build_{taxon}_db.py          # 각 패키지 DB 빌드 → db/ (×11)
│   ├── build_{taxon}_scoda.py       # 각 패키지 .scoda → dist/ (×11)
│   ├── build_paleocore_db.py        # PaleoCore DB → db/
│   ├── build_paleocore_scoda.py     # paleocore.scoda → dist/
│   ├── build_paleobase_scoda.py     # paleobase.scoda (메타 패키지) → dist/
│   ├── validate_trilobita_db.py     # DB 검증 (17 checks)
│   ├── build_all.py                 # 전체 빌드
│   ├── db_path.py                   # DB 경로 헬퍼
│   └── archive/                     # 레거시 스크립트 보관
├── tests/
│   ├── conftest.py                  # Shared fixtures
│   └── test_trilobase.py            # Trilobase domain tests (117)
├── vendor/                           # Third-party reference data
├── devlog/                           # 작업 기록
│   ├── YYYYMMDD_NNN_*.md           # 작업 로그
│   ├── YYYYMMDD_PNN_*.md           # 계획(Plan) 문서
│   └── YYYYMMDD_RNN_*.md           # 리뷰(Review) 문서
└── docs/
    ├── canonical_vs_assertion.md     # 두 DB 구조 비교
    ├── source_data_guide.md          # 소스 데이터 가이드
    ├── PDF_SOURCE_STATUS.md          # Treatise PDF/TSF/SCODA 현황표
    └── Taxonomic Source Format Specification v0.1.md  # TSF 사양서
```

## Dependencies

- **scoda-engine** (`pip install -e /mnt/d/projects/scoda-engine[dev]`): SCODA runtime (FastAPI, MCP, GUI, .scoda package support)
- Tests import from `scoda_engine.app`, `scoda_engine.scoda_package`

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
2. **HANDOFF.md 갱신**: `HANDOFF.md` 업데이트
   - 완료된 작업 목록, 테이블 목록, 파일 구조, 진행 상태 반영
3. **README.md 갱신** (해당 시): 사용자가 알아야 할 새 기능이 있으면 반영

이 3가지를 별도 커밋으로 기록 (코드 커밋과 분리).
