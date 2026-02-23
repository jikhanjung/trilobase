# 090: CI/CD GitHub Actions 구현

**Date:** 2026-02-23
**Type:** Implementation
**Plan:** P68

## 작업 내용

P68 계획에 따라 GitHub Actions CI/CD 파이프라인을 구현했다.

### 생성 파일

| 파일 | 용도 |
|------|------|
| `.github/workflows/ci.yml` | push/PR to main 시 pytest 자동 실행 |
| `.github/workflows/release.yml` | `v*.*.*` 태그 push 시 자동 릴리스 |
| `.github/workflows/manual-release.yml` | GitHub Actions UI에서 수동 릴리스 |

### ci.yml

- **트리거**: push to main, PR to main
- **단계**: checkout → scoda-engine clone → core 설치 → scoda-engine 설치 → pytest

### release.yml (자동)

- **트리거**: `v*.*.*` 태그 push
- **단계**: checkout → scoda-engine clone → 설치 → pytest (gate) → .scoda 빌드 → GitHub Release 생성
- **artifact**: `trilobase.scoda`, `paleocore.scoda`
- **릴리스 액션**: `softprops/action-gh-release@v2`

### manual-release.yml (수동)

- **트리거**: `workflow_dispatch` (GitHub Actions 탭에서 Run workflow)
- **입력**: version_tag, prerelease (boolean), release_notes (선택)
- **단계**: release.yml과 동일 (테스트 → 빌드 → Release 생성)

## 트러블슈팅

### scoda-engine-core 의존성 오류

초기 CI 실행 시 `scoda-engine-core` 패키지를 찾을 수 없어 실패:

```
ERROR: No matching distribution found for scoda-engine-core<1.0.0,>=0.1.0
```

**원인**: `scoda-engine`이 `scoda-engine-core`에 의존하는데, 이 패키지는 PyPI에 없고 `scoda-engine/core/` 하위 디렉토리에 존재.

**해결**: `pip install -e "./scoda-engine/core"`를 scoda-engine 설치 전에 추가.

## 커밋 이력

| 커밋 | 내용 |
|------|------|
| `53cf444` | ci.yml, release.yml 생성 |
| `df84473` | scoda-engine-core 설치 순서 수정 |
| `674f926` | manual-release.yml 추가 |
