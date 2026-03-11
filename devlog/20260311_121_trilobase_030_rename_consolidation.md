# 121: Trilobase 0.3.0 — 이름 통합 + is_accepted 제거 + 스크립트 정리

**날짜**: 2026-03-11

## 요약

assertion-centric DB를 trilobase 본류로 통합. `trilobase-assertion` → `trilobase`로 이름 변경,
버전 0.3.0 발행. `is_accepted` 컬럼 제거, 스크립트 이름 통일, 레거시 스크립트 archive 이동.

## 주요 변경

### 1. is_accepted 컬럼 제거
- assertion 테이블에서 `is_accepted` 컬럼 삭제
- `classification_edge_cache` 기반으로 완전 대체
- v_taxonomy_tree, v_taxonomic_ranks 뷰를 edge_cache 기반으로 재작성
- ui_queries 5개 수정 (taxon_detail, taxon_assertions, genus_hierarchy, reference_assertions, assertion_list)
- CTE 성능 문제 해소 (assertion 테이블 스캔 → edge_cache PK 인덱스 활용)

### 2. 이름 통합: trilobase-assertion → trilobase
- artifact_id: `trilobase-assertion` → `trilobase`
- DB 파일: `trilobase-0.3.0.db`
- .scoda 패키지: `trilobase-0.3.0.scoda`
- 기존 canonical DB: `trilobase-0.2.6.db` → `trilobase-canonical-0.2.6.db`로 리네임
- `db_path.py`에 `find_canonical_db()` 추가, `_CANONICAL_RE` 패턴 분리

### 3. 스크립트 이름 통일
| 기존 | 변경 후 |
|------|---------|
| `build_assertion_db.py` | `build_trilobase_db.py` |
| `create_assertion_scoda.py` | `build_trilobase_scoda.py` |
| `create_assertion_db.py` | 통합 (아래 참조) |
| `validate_assertion_db.py` | `validate_trilobase_db.py` |
| `create_paleocore.py` | `build_paleocore_db.py` |
| `create_paleocore_scoda.py` | `build_paleocore_scoda.py` |
| `create_scoda.py` | `build_all.py` |

### 4. _trilobase_queries.py 통합
- `_trilobase_queries.py`(구 `create_assertion_db.py`)에서 `_build_queries()`와 `_build_manifest()`만
  `build_trilobase_db.py`로 직접 이동
- dynamic import (`importlib.util`) 제거
- 레거시 파일은 `scripts/archive/`로 이동

### 5. 레거시 스크립트 archive 이동
- 60+ 스크립트를 `scripts/archive/`로 이동
- `scripts/`에는 빌드 파이프라인 스크립트만 유지:
  - `build_trilobase_db.py`, `build_trilobase_scoda.py`, `validate_trilobase_db.py`
  - `build_paleocore_db.py`, `build_paleocore_scoda.py`
  - `build_all.py`, `db_path.py`

### 6. 문서 추가
- `docs/canonical_vs_assertion.md` — 두 DB 구조의 비프로그래머 대상 설명
- `docs/source_data_guide.md` — 소스 데이터 작성 가이드

### 7. UI 변경
- "Classification Profile" 라벨 → "Profile"로 축약

## DB 통계 (0.3.0)
- taxon: 5,627
- reference: 2,135
- assertion: 8,382 (PLACED_IN 7,305 / SYNONYM_OF 1,075 / SPELLING_OF 2)
- edge_cache: 8,930 (default 5,113 / treatise1959 1,772 / treatise2004 2,045)
- .scoda: 1.3 MB

## 검증
- validate_trilobase_db.py: 17/17 통과
