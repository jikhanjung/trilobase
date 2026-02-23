# P68: CI/CD + GitHub Actions Release

**Date:** 2026-02-23
**Type:** Plan
**Status:** Implemented

## 목표

trilobase 레포에 GitHub Actions 기반 CI/CD 파이프라인 구축:
- **CI**: push/PR 시 pytest 자동 실행
- **CD**: Git tag (`v*.*.*`) push 시 자동 릴리스 (GitHub Release + .scoda 첨부)

## 결정사항

| 항목 | 결정 |
|------|------|
| 대상 레포 | trilobase만 |
| 릴리스 artifact | `trilobase.scoda` + `paleocore.scoda` |
| 릴리스 트리거 | Git tag (`v*.*.*`) |
| CI 테스트 | push/PR 시 pytest 자동 실행 |
| scoda-engine 의존성 | CI에서 GitHub clone → `pip install -e` |

## 구현 계획

### 파일 1: `.github/workflows/ci.yml`

- **트리거**: `push` to main, `pull_request` to main
- **환경**: ubuntu-latest, Python 3.11
- **단계**: checkout → scoda-engine clone → pip install → pytest

### 파일 2: `.github/workflows/release.yml`

- **트리거**: tag push (`v*.*.*`)
- **환경**: ubuntu-latest, Python 3.11
- **단계**: checkout → scoda-engine clone → pip install → pytest (gate) → .scoda 빌드 → GitHub Release 생성
- **릴리스 액션**: `softprops/action-gh-release@v2`
- **퍼미션**: `contents: write`

## 릴리스 워크플로 (사용법)

```bash
# 1. CHANGELOG.md 업데이트
# 2. 버전 범프
python scripts/bump_version.py trilobase 0.2.3
# 3. 커밋
git add -A && git commit -m "release: v0.2.3"
# 4. 태그 + 푸시 → 자동 릴리스
git tag v0.2.3
git push origin main --tags
```

## 주의사항

- scoda-engine 레포가 **public**이어야 CI에서 clone 가능 (private이면 deploy key/PAT 필요)
- `db/trilobase.db`가 git tracked 상태여야 .scoda 빌드 가능 (현재 OK)
- 17개 테스트가 실제 DB 직접 읽으므로 checkout만 되면 동작

## 테스트 수 분석 (101개)

| fixture | 수 | 의존성 |
|---------|-----|--------|
| `client` (FastAPI TestClient) | 51 | scoda_engine.app 필요 |
| `test_db` (SQLite 직접) | 28 | scoda_engine.scoda_package 필요 |
| `self` only | 17 | db/trilobase.db 직접 읽기 |
| 기타 (`tmp_path` 등) | 5 | scoda_engine.scoda_package 필요 |
