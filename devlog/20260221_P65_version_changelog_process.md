# 버전 관리 + Changelog 프로세스 구현

**날짜:** 2026-02-21
**유형:** 계획(Plan)

## Context

trilobase/paleocore 모두 version 0.1.0이지만, 이후 상당한 변경이 누적됨 (taxon_bibliography 테이블, family 재배치, 데이터 품질 수정 등). 버전업 프로세스와 변경 이력을 패키지에 포함시켜야 함.

## 버전 체계

- **Major**: 스키마 변경 (테이블 추가/삭제, 컬럼 변경)
- **Minor**: 유의미한 데이터 추가/변경
- **Patch**: 데이터 품질 수정 (오타, 연결 수정)

## 구현 항목

### 1. `CHANGELOG.md` 파일 생성 (trilobase, paleocore 각각)

- `CHANGELOG.md` (trilobase 루트) — trilobase 패키지 changelog
- `CHANGELOG_paleocore.md` (trilobase 루트) — paleocore 패키지 changelog
- 형식: [Keep a Changelog](https://keepachangelog.com/) 기반
- 수동 작성 (devlog와 별도 — devlog는 작업 기록, changelog는 릴리스 기록)

### 2. `scripts/bump_version.py` 스크립트

역할: 버전 번호를 DB와 스크립트에서 일괄 갱신

```
python scripts/bump_version.py trilobase 0.2.0
python scripts/bump_version.py paleocore 0.1.1
```

동작:
1. 대상 DB의 `artifact_metadata` 테이블에서 `version` 값 업데이트
2. `create_scoda.py`의 paleocore dependency version 하드코딩 동기화 (trilobase 버전업 시)
3. 현재 버전 → 새 버전 변경 사항 출력
4. `--dry-run` 지원

갱신 대상:
- `db/trilobase.db` → `artifact_metadata` SET value WHERE key='version'
- `db/paleocore.db` → `artifact_metadata` SET value WHERE key='version'
- `scripts/create_scoda.py` → paleocore dependency version (line 104, 136)

### 3. `.scoda` 패키지에 CHANGELOG.md 포함

- `ScodaPackage.create()` 호출 시 `extra_assets`에 CHANGELOG.md 추가
- `scripts/create_scoda.py`: `extra_assets['CHANGELOG.md'] = 'CHANGELOG.md'`
- `scripts/create_paleocore_scoda.py`: `extra_assets['CHANGELOG.md'] = 'CHANGELOG_paleocore.md'`
- .scoda ZIP 구조: `manifest.json`, `data.db`, `CHANGELOG.md`, `assets/`, ...

### 4. 초기 CHANGELOG 내용 작성

0.1.0 이후 변경 사항을 정리하여 최초 changelog 작성.

## 수정 대상 파일

| 파일 | 변경 |
|------|------|
| `CHANGELOG.md` | **신규** — trilobase changelog |
| `CHANGELOG_paleocore.md` | **신규** — paleocore changelog |
| `scripts/bump_version.py` | **신규** — 버전 갱신 스크립트 |
| `scripts/create_scoda.py` | extra_assets에 CHANGELOG.md 추가 |
| `scripts/create_paleocore_scoda.py` | extra_assets에 CHANGELOG.md 추가 |

## 검증

1. `python scripts/bump_version.py trilobase 0.2.0 --dry-run` → 변경 대상 확인
2. `python scripts/bump_version.py trilobase 0.2.0` → DB 업데이트 확인
3. `python scripts/create_scoda.py --dry-run` → manifest version 확인
4. `pytest tests/` → 기존 테스트 통과
