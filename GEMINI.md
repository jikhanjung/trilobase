# GEMINI.md

This file provides guidance to Gemini Code when working with code in this repository.

## Quick Start

**새 세션 시작 시 반드시 `docs/HANDOVER.md`를 먼저 읽을 것.** 현재 프로젝트 상태, 진행 중인 작업, 다음 단계가 정리되어 있음.

## Project Overview

Trilobase is a paleontological database project focused on trilobite taxonomy. The goal is to clean, normalize, and import trilobite genus data from Jell & Adrain (2002) into a structured database.

## Repository Structure

```
trilobase/
├── trilobite_genus_list.txt          # 최신 버전 (항상 이 파일 수정)
├── trilobite_genus_list_original.txt # 원본 백업
├── trilobite_genus_list_*.txt        # 각 단계별 중간 파일
├── trilobite_family_list.txt         # Family 목록
├── trilobite_nomina_nuda.txt         # Nomina nuda
├── scripts/                          # 데이터 처리 스크립트
├── devlog/                           # 작업 기록
│   └── YYYYMMDD_NNN_*.md            # 일별 작업 로그
└── docs/
    └── HANDOVER.md                   # 인수인계 문서 (필독)
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

- `trilobite_genus_list.txt`가 항상 최신 버전
- 각 Phase 완료 시 반드시 git commit
- 중간 과정 파일은 `_단계명.txt` 접미사로 보존
- 작업 기록은 `devlog/YYYYMMDD_NNN_제목.md` 형식
