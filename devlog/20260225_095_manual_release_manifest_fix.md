# 095. manual-release.yml Hub Manifest 업로드 누락 수정

**Date:** 2026-02-25

## 문제

`release.yml`(tag push 트리거)에는 `dist/*.manifest.json`이 Release assets에 포함되어 있었으나,
`manual-release.yml`(workflow_dispatch 트리거)에는 누락되어 있었음.

`create_scoda.py` 실행 시 hub manifest 파일이 `dist/`에 자동 생성되지만,
manual release 시에는 GitHub Release에 업로드되지 않는 상태였음.

## 수정 내용

- `.github/workflows/manual-release.yml`: Release assets `files` 섹션에 `dist/*.manifest.json` 추가

## 변경 파일

- `.github/workflows/manual-release.yml`
