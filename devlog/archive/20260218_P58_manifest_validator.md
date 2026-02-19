# P58: Manifest Validator / Linter

**작성일:** 2026-02-18
**상태:** 계획 → 구현 중

## 배경

.scoda 패키지 빌드 시 manifest JSON의 누락/불일치를 사전 검출하는 검증 스크립트 추가.
과거 반복된 manifest 버그 방지 목적:
- PaleoCore `chart_options` 필수 키 누락 → 정렬/색상 깨짐
- `on_row_click.detail_view`가 존재하지 않는 뷰 참조
- `source_query`가 삭제된 named query 참조 → 404
- `sub_queries`의 `result.<field>` 파라미터가 source query 출력에 없는 필드 참조

## 구현 계획

### Step 1: `scripts/validate_manifest.py` 생성 (~170줄)

**공개 API:**
```python
def validate_db(db_path: str) -> tuple[list[str], list[str]]:
    """DB 파일의 ui_manifest를 검증. (errors, warnings) 반환."""
```

**검증 규칙:**

| 검사 | 심각도 | 이유 |
|------|--------|------|
| `default_view`가 views에 없음 | ERROR | 로드 시 크래시 |
| view `type` 누락 또는 미인식 | ERROR | 렌더링 불가 |
| `source_query`가 ui_queries에 없음 | ERROR | 런타임 실패 |
| `on_row_click.detail_view`가 views에 없음 | ERROR | 클릭 시 크래시 |
| table `default_sort.key`가 columns에 없음 | ERROR | 정렬 실패 |
| tree `tree_options` 필수 키 누락 | ERROR | 트리 빌드 실패 |
| tree `item_query`가 ui_queries에 없음 | ERROR | leaf 로딩 실패 |
| chart `chart_options` 필수 키 누락 | ERROR | 차트 깨짐 |
| detail `sub_queries[*].query`가 ui_queries에 없음 | ERROR | composite 실패 |
| `linked_table`/`raw_text` 섹션에 `data_key` 없음 | ERROR | KeyError |
| `field_grid` 섹션에 `fields` 없음 | ERROR | 빈 섹션 |
| table에 `on_row_click` 없음 | WARNING | UX 권장사항 |
| 미인식 section type | WARNING | 커스텀 확장 허용 |

**내부 함수 구조:**
- `validate_manifest(manifest, named_queries, views)` — 순수 함수
- `_validate_view()` → 뷰 타입별 dispatch
- 타입별: `_validate_table_view()`, `_validate_tree_view()`, `_validate_chart_view()`, `_validate_hierarchy_view()`, `_validate_detail_view()`

**CLI:**
```bash
python scripts/validate_manifest.py trilobase.db
python scripts/validate_manifest.py paleocore.db
# exit code 0: 에러 없음, exit code 1: 에러 있음
```

### Step 2: 빌드 스크립트 통합

`create_scoda.py`, `create_paleocore_scoda.py`에서 `ScodaPackage.create()` 호출 직전 + dry-run 모드에서도 검증.

### Step 3: 테스트 (~14개)

`tests/test_runtime.py`에 `TestManifestValidator` 클래스 추가.

### Step 4: devlog + HANDOVER 갱신

## 수정 파일

| 파일 | 작업 |
|------|------|
| `scripts/validate_manifest.py` | **신규** (~170줄) |
| `scripts/create_scoda.py` | 수정 (~8줄) |
| `scripts/create_paleocore_scoda.py` | 수정 (~8줄) |
| `tests/test_runtime.py` | 수정 (~14개 테스트) |
