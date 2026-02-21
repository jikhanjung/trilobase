# 085: 버전 관리 + Changelog 프로세스 구현

**날짜:** 2026-02-21
**계획 문서:** `devlog/20260221_P65_version_changelog_process.md`

## 배경

trilobase/paleocore 모두 0.1.0이었지만, 이후 상당한 변경이 누적됨 (taxon_bibliography 테이블, family 재배치, 데이터 품질 수정 등). 버전업 프로세스와 변경 이력을 체계화할 필요.

## 버전 체계

- **Major**: 스키마 변경 (테이블 추가/삭제, 컬럼 변경)
- **Minor**: 유의미한 데이터 추가/변경
- **Patch**: 데이터 품질 수정 (오타, 연결 수정)

## 구현 내용

### 1. CHANGELOG 파일 (2개)

- `CHANGELOG.md` — trilobase 패키지 changelog
  - 0.1.0: 초기 릴리스 (taxonomic_ranks, synonyms, bibliography 등)
  - 0.2.0: taxon_bibliography, taxonomic_opinions, 데이터 품질 수정 다수
- `CHANGELOG_paleocore.md` — paleocore 패키지 changelog
  - 0.1.0: 초기 릴리스 (countries, formations, ics_chronostrat 등)
  - 0.1.1: formations metadata 채우기, countries 품질 정리

형식: [Keep a Changelog](https://keepachangelog.com/) 기반.

### 2. `scripts/bump_version.py`

```
python scripts/bump_version.py trilobase 0.2.0 [--dry-run]
python scripts/bump_version.py paleocore 0.1.1 [--dry-run]
```

갱신 대상:
- DB `artifact_metadata` 테이블의 `version` 값
- `create_scoda.py`의 paleocore dependency version (paleocore 버전업 시)

기능:
- 현재 버전 → 새 버전 변경 사항 출력
- `--dry-run`: 실제 수정 없이 변경 대상만 표시
- 이미 동일 버전이면 조기 종료

### 3. .scoda 패키지에 CHANGELOG 포함

- `scripts/create_scoda.py`: `extra_assets['CHANGELOG.md'] = 'CHANGELOG.md'`
- `scripts/create_paleocore_scoda.py`: `extra_assets['CHANGELOG.md'] = 'CHANGELOG_paleocore.md'`

### 4. 버전 범프 적용

| 패키지 | 이전 | 이후 |
|--------|------|------|
| trilobase | 0.1.0 | **0.2.0** |
| paleocore | 0.1.0 | **0.1.1** |

trilobase → 0.2.0 (Minor): taxon_bibliography/taxonomic_opinions 테이블 추가 (스키마 변경이지만 첫 정식 릴리스 전이므로 Minor)
paleocore → 0.1.1 (Patch): formations metadata 보강, countries 품질 수정

## 수정 파일

| 파일 | 변경 |
|------|------|
| `CHANGELOG.md` | **신규** |
| `CHANGELOG_paleocore.md` | **신규** |
| `scripts/bump_version.py` | **신규** |
| `scripts/create_scoda.py` | extra_assets에 CHANGELOG.md 추가, paleocore dep 0.1.0→0.1.1 |
| `scripts/create_paleocore_scoda.py` | extra_assets에 CHANGELOG.md 추가 |
| `db/trilobase.db` | artifact_metadata version 0.1.0→0.2.0 |
| `db/paleocore.db` | artifact_metadata version 0.1.0→0.1.1 |

## 검증

- `python scripts/bump_version.py trilobase 0.2.0 --dry-run` ✅
- `python scripts/bump_version.py paleocore 0.1.1 --dry-run` ✅
- `python scripts/create_scoda.py --dry-run` → manifest version 0.2.0, paleocore dep 0.1.1 ✅
- `pytest tests/` → 82개 전부 통과 ✅
