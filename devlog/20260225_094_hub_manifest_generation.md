# 094: Hub Manifest 자동 생성 추가

**Date:** 2026-02-25

## 배경

SCODA Hub 정적 레지스트리 스펙(`scoda-engine/docs/HUB_MANIFEST_SPEC.md` v1.0)에 따라,
`.scoda` 패키지 릴리스 시 Hub Manifest JSON 파일을 함께 생성·업로드해야 한다.
Hub Manifest는 `.scoda`를 열지 않고도 패키지 메타데이터(SHA-256, 의존성, 크기 등)를
확인할 수 있게 하며, Hub Index 수집기가 이를 파싱하여 카탈로그에 반영한다.

## 변경 내용

### 1. `scripts/create_scoda.py`

- `generate_hub_manifest()` 함수 추가
  - DB의 `artifact_metadata`와 `provenance` 테이블에서 메타데이터 자동 수집
  - `.scoda` 파일의 SHA-256 해시 계산
  - 파일명: `{package_id}-{version}.manifest.json` (스펙 준수)
- `.scoda` 빌드 직후 자동 호출
- 출력 예: `dist/trilobase-0.2.3.manifest.json`

### 2. `scripts/create_paleocore_scoda.py`

- 동일한 `generate_hub_manifest()` 함수 추가
- 의존성 없음(`dependencies: {}`)으로 설정
- 출력 예: `dist/paleocore-0.1.1.manifest.json`

### 3. `.github/workflows/release.yml`

- Release asset 업로드에 `dist/*.manifest.json` 추가

### 4. `docs/HANDOFF.md`

- UI/Manifest 섹션의 완료된 4개 항목 ✅ 처리

## Hub Manifest 출력 예시

```json
{
  "hub_manifest_version": "1.0",
  "package_id": "trilobase",
  "version": "0.2.3",
  "title": "Trilobase - Trilobite genus-level taxonomy database based on Jell & Adrain (2002)",
  "license": "CC-BY-4.0",
  "dependencies": { "paleocore": ">=0.1.1,<0.2.0" },
  "filename": "trilobase-0.2.3.scoda",
  "sha256": "3dc5cf33...",
  "size_bytes": 1496356,
  "engine_compat": ">=0.1.0"
}
```

## 테스트

- 빌드 테스트: trilobase, paleocore 모두 `.scoda` + `.manifest.json` 정상 생성
- 기존 테스트: 101개 전체 통과 (영향 없음)
