# GEMINI.md

This file provides guidance to Gemini Code when working with code in this repository.

## Quick Start

**새 세션 시작 시 반드시 `docs/HANDOFF.md`를 먼저 읽을 것.** 현재 프로젝트 상태, 진행 중인 작업, 다음 단계가 정리되어 있음.

## Project Overview

Trilobase is a paleontological database project focused on trilobite taxonomy. The goal is to clean, normalize, and import trilobite genus data from Jell & Adrain (2002) into a structured database.

## Repository Structure

**Runtime engine** (`scoda-engine`)은 별도 repo: `/mnt/d/projects/scoda-engine`
- `pip install -e /mnt/d/projects/scoda-engine[dev]`로 설치
- import: `from scoda_engine.app import app` 등

```
trilobase/                                 # 도메인 데이터/스크립트/테스트만
├── pytest.ini                             # pytest config
├── requirements.txt                       # scoda-engine 의존
├── db/                                    # Canonical DB (git tracked)
│   ├── trilobase.db                       # Trilobase SQLite DB
│   └── paleocore.db                       # PaleoCore 참조 DB
├── dist/                                  # 생성 산출물 (gitignored)
│   ├── trilobase.scoda                    # .scoda 패키지
│   ├── paleocore.scoda
│   └── *_overlay.db                       # Overlay DB
├── data/                                  # 소스 데이터 파일
│   ├── trilobite_genus_list.txt           # 최신 버전 (항상 이 파일 수정)
│   ├── trilobite_family_list.txt          # Family 목록
│   └── adrain2011.txt                     # Suprafamilial taxa
├── scripts/                               # 도메인 스크립트
├── spa/                                   # Reference SPA
├── tests/
│   ├── conftest.py
│   └── test_trilobase.py                  # 도메인 테스트 (66개)
├── devlog/                                # 작업 기록
│   └── YYYYMMDD_NNN_*.md
└── docs/
    └── HANDOFF.md                         # 인수인계 문서 (필독)
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
- 작업 기록은 `devlog/YYYYMMDD_NNN_제목.md` 형식
