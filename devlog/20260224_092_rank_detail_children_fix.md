# 092: rank_detail Children 테이블 버그 수정 및 redirect 기능

**Date:** 2026-02-24

## 문제

Family detail 페이지에서 Children 테이블이 비어 보임.

### 원인

1. `rank_detail` 매니페스트의 Children 섹션이 `type: "rank_children"`으로 정의됨
2. SPA `renderDetailSection`에 `rank_children` 타입 핸들러가 없음 → default fallback
3. fallback이 `renderLinkedTable`을 호출하지만 `columns` 정의가 없어 빈 테이블 렌더링

## 수정 사항

### 1. Children 섹션 타입 변경 (`add_scoda_manifest.py`)

- `type: "rank_children"` → `type: "linked_table"`
- `columns` 추가: Name, Rank, Author, Genera (with condition)
- `on_row_click` 유지: `rank_detail`로 연결

### 2. rank_detail → genus_detail redirect (`scoda-engine app.js`)

- `renderDetailFromManifest`에 범용 `redirect` 지원 추가
- 매니페스트 `redirect: {"key": "field_name", "map": {"value": "target_view"}}` 형식
- rank_detail에 `redirect: {"key": "rank", "map": {"Genus": "genus_detail"}}` 적용
- SPA가 도메인 필드를 하드코딩하지 않아 범용성 유지

### 3. create_database.py 레거시 인덱스 제거

- `taxa`가 VIEW로 전환된 이후 `CREATE INDEX ON taxa(...)` 에러 발생
- 더 이상 사용되지 않는 인덱스 코드 삭제

## 변경된 파일

| 파일 | 리포 | 변경 |
|------|------|------|
| `scripts/add_scoda_manifest.py` | trilobase | Children 섹션 type/columns, redirect 추가 |
| `scripts/create_database.py` | trilobase | 레거시 인덱스 코드 제거 |
| `db/trilobase.db` | trilobase | 매니페스트 + 버전 0.2.3 반영 |
| `CHANGELOG.md` | trilobase | 0.2.3 항목 추가 |
| `scoda_engine/static/js/app.js` | scoda-engine | redirect 기능 추가 |

## 테스트

- trilobase: 101 tests passing
