# 122: Brachiobase UI 개선 + P85 계획 문서

**날짜:** 2026-03-13

## 변경 내용

### 1. Brachiobase 빌드 스크립트 개선 (`build_brachiobase_db.py`)

**버그 수정:**
- `taxon_detail_view`의 `id_param` → `source_param`으로 수정 (composite detail 404 원인)
- `rank_radius`에 Phylum(0.03)과 Subphylum(0.06) 추가 (기존에 누락)

**UI 추가:**
- **Tree Chart 뷰**: radial/rectangular 레이아웃 지원 트리 시각화 탭
- **Profile Comparison compound 뷰**: Treatise 1965 vs Revised 2000-2006 비교
  - Diff Table: 이동/추가/삭제 taxa 목록 (색상 코딩)
  - Diff Tree: 차이를 색으로 표시한 단일 트리
  - Side-by-Side: 두 프로필 나란히 비교
  - Animation: 두 트리 간 모핑 애니메이션
- `profile_diff`, `profile_diff_edges` 쿼리 추가

### 2. P85 계획 문서 (`devlog/20260312_P85_base_taxonomy_template.md`)

Taxonomy 기반 SCODA 패키지의 공통 쿼리/UI를 `scoda_engine_core.taxonomy_base` 모듈로 추출하는 계획.
- TaxonomyConfig dataclass + base_queries() + base_manifest() + merge 헬퍼
- 5 Phase 구현 계획 (공통 쿼리 → manifest → brachiobase 마이그레이션 → trilobase 마이그레이션 → 문서화)

### 3. DB 리빌드

- `trilobase-0.3.0.db`: 재빌드 (변경 없음, checksum 갱신)
- `brachiobase-0.2.0.db`: UI 뷰 추가 반영 (7개 뷰: Taxonomy, Genera, Assertions, References, Tree, Comparison, Taxon Detail)

## 수정 파일

| 파일 | 변경 |
|------|------|
| `scripts/build_brachiobase_db.py` | source_param 수정, rank_radius 수정, tree_chart + comparison 추가 |
| `db/brachiobase-0.2.0.db` | UI 뷰 추가 반영 |
| `db/trilobase-0.3.0.db` | 재빌드 |
| `devlog/20260312_P85_base_taxonomy_template.md` | 신규 계획 문서 |

## 테스트

- trilobase: 117 passed
- scoda-engine: 250 passed
