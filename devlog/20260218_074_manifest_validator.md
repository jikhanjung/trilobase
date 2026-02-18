# 074: Manifest Validator / Linter (A-2)

**날짜:** 2026-02-18
**계획 문서:** `devlog/20260218_P58_manifest_validator.md`

## 작업 내용

.scoda 패키지 빌드 시 manifest JSON의 누락/불일치를 사전 검출하는 검증 스크립트 추가.

### 새 파일

- `scripts/validate_manifest.py` (~170줄)
  - `validate_db(db_path)` → `(errors, warnings)` — DB 파일의 ui_manifest 검증
  - `validate_manifest(manifest, named_queries)` → 순수 함수 (DB 접근 없음)
  - CLI: `python scripts/validate_manifest.py <db_path>` (exit code 0/1)

### 검증 규칙 (13개)

| 검사 | 심각도 |
|------|--------|
| `default_view`가 views에 없음 | ERROR |
| view `type` 누락 또는 미인식 | ERROR |
| `source_query`가 ui_queries에 없음 | ERROR |
| `on_row_click.detail_view`가 views에 없음 | ERROR |
| table `default_sort.key`가 columns에 없음 | ERROR |
| tree `tree_options` 필수 키 누락 | ERROR |
| tree `item_query`가 ui_queries에 없음 | ERROR |
| chart `chart_options` 필수 키 누락 | ERROR |
| detail `sub_queries[*].query`가 ui_queries에 없음 | ERROR |
| `linked_table` 섹션에 `data_key` 없음 | ERROR |
| `field_grid` 섹션에 `fields` 없음 | ERROR |
| table에 `on_row_click` 없음 | WARNING |
| 미인식 section type | WARNING |

### 빌드 스크립트 통합

- `scripts/create_scoda.py`: `ScodaPackage.create()` 호출 전에 `validate_db()` 삽입
- `scripts/create_paleocore_scoda.py`: 동일 패턴
- dry-run 모드에서도 검증 실행

### 수정 파일

| 파일 | 작업 |
|------|------|
| `scripts/validate_manifest.py` | **신규** — 검증 스크립트 |
| `scripts/create_scoda.py` | 수정 — validate_db 호출 추가 |
| `scripts/create_paleocore_scoda.py` | 수정 — validate_db 호출 추가 |
| `tests/test_runtime.py` | 수정 — TestManifestValidator 14개 테스트 추가 |

## 테스트

- TestManifestValidator: 14개 테스트 전부 통과
- 전체 테스트: 245개 전부 통과 (기존 231 + 신규 14)
- 실제 DB 검증: `trilobase.db` OK, `paleocore.db` OK
