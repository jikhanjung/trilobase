# Trilobase Project Handover

**Last updated:** 2026-03-11

## Project Overview

A trilobite taxonomic database project. Genus data extracted from Jell & Adrain (2002) PDF is cleaned, normalized, and distributed as a SCODA package.

- **SCODA Engine** (runtime): separate repo at `/mnt/d/projects/scoda-engine` (`pip install -e /mnt/d/projects/scoda-engine[dev]`)
- **Completed Phase 1~46 details**: see [HISTORY.md](design/HISTORY.md)

## Current Status

| Item | Value |
|------|-------|
| Trilobase version | **0.3.0** (assertion-centric 통합) |
| PaleoCore version | 0.1.1 |
| taxon | 5,627 |
| reference | 2,135 |
| assertion | 8,382 (PLACED_IN 7,305 + SYNONYM_OF 1,075 + SPELLING_OF 2) |
| classification_edge_cache | 8,930 (default 5,113 / treatise1959 1,772 / treatise2004 2,045) |
| classification_profile | 3 (default, treatise1959, treatise2004) |
| genus_formations | 4,503 |
| genus_locations | 4,849 |
| taxon_reference | 4,173 |
| ui_queries | 46 |
| Tests | 118 passing |
| Legacy canonical DB | `trilobase-canonical-0.2.6.db` (보존) |

## Database Status

**Trilobase DB (trilobase-0.3.0.db) — assertion-centric 통합:**

| Table/View | Records | Description |
|------------|---------|-------------|
| taxon | 5,627 | All taxa (Class~Genus + Subfamily + placeholders) |
| assertion | 8,382 | PLACED_IN 7,305 + SYNONYM_OF 1,075 + SPELLING_OF 2 |
| reference | 2,135 | Bibliography + JA2002 + Treatise ch4/ch5 |
| classification_profile | 3 | default, treatise1959, treatise2004 |
| classification_edge_cache | 8,930 | default 5,113 / treatise1959 1,772 / treatise2004 2,045 |
| genus_formations | 4,503 | Genus-Formation many-to-many |
| genus_locations | 4,849 | Genus-Country many-to-many |
| taxon_reference | 4,173 | Taxon↔Reference FK links |
| artifact_metadata | — | SCODA artifact metadata |
| provenance | — | Data provenance |
| schema_descriptions | — | Table/column descriptions |
| ui_display_intent | — | SCODA view type hints |
| ui_queries | 46 | Named SQL queries |
| ui_manifest | 1 | Declarative view definitions (JSON) |
| synonyms (view) | — | Backward-compat VIEW |
| v_taxonomy_tree (view) | — | edge_cache 기반 트리 뷰 |
| v_taxonomic_ranks (view) | — | edge_cache 기반 랭크 뷰 |

**Legacy canonical DB**: `trilobase-canonical-0.2.6.db` (기존 taxonomic_ranks 기반, 보존용)

## Build Pipeline

```bash
# 전체 빌드 (DB + .scoda 패키지)
python scripts/build_all.py

# 개별 빌드
python scripts/build_trilobase_db.py          # → db/trilobase-0.3.0.db
python scripts/build_paleocore_db.py           # → db/paleocore-0.1.1.db
python scripts/build_trilobase_scoda.py        # → dist/trilobase-0.3.0.scoda
python scripts/build_paleocore_scoda.py        # → dist/paleocore-0.1.1.scoda
python scripts/validate_trilobase_db.py        # → 17/17 검증 통과

# Admin 모드로 실행
python -m scoda_engine.serve --db-path db/trilobase-0.3.0.db --mode admin --port 8090
```

## History (완료된 주요 작업)

### Modular Rebuild Pipeline (P72/P73) ✅
소스 텍스트로부터 canonical DB를 한 번에 재생성하는 파이프라인. 현재 `scripts/archive/`에 보존.

### Assertion-Centric DB (P74~P80) ✅
- P74: assertion-centric 모델 구현 (taxon/assertion/reference/classification_profile)
- P76: Radial Tree 뷰
- P77: Versioned DB filename (`{name}-{version}.db`)
- P78: Treatise 2004 Import (Agnostida + Redlichiida)
- P79: Profile-Based Taxonomy Tree + Profile Selector UI
- P80: Manifest-Driven CRUD (Admin 모드에서 웹 UI CRUD)

### Treatise 1959/2004 Import ✅
- 1959 Treatise Part O: 8 orders, 13 suborders, 33 superfamilies, 142 families, 128 subfamilies, 1,014 genera
- 2004 Treatise: Agnostida + Redlichiida 분류 교체
- TXT → JSON 파이프라인 (`parse_treatise_txt.py`)

### Profile Comparison (R02) ✅
- Diff Table, Diff Tree, Side-by-Side, Morphing 애니메이션 4가지 비교 뷰
- Compound View로 통합 (sub-view 탭)
- `TreeChartInstance` 클래스 리팩토링 + 듀얼 렌더링

### Source-Driven Build (v0.2.0) ✅
- `data/sources/*.txt` 기반 단일 스크립트 빌드
- Family 이름 정규화, canonical opinions 임포트, Treatise 직접 파싱

### Trilobase 0.3.0: 이름 통합 ✅
- `trilobase-assertion` → `trilobase`로 통합, assertion-centric 모델이 메인
- `is_accepted` 컬럼 제거 → `classification_edge_cache` 기반 뷰로 전환
- 스크립트 이름 통일 (`build_trilobase_*`, `build_paleocore_*`, `build_all`)
- `_trilobase_queries.py`를 `build_trilobase_db.py`에 통합
- 60+ 레거시 스크립트 → `scripts/archive/`
- **상세**: `devlog/20260311_121_trilobase_030_rename_consolidation.md`

### 설계 리뷰 문서
- **R01**: 시간에 따라 변화하는 Taxonomy 관리 — `devlog/20260302_R01_taxonomy_management.md`
- **R02**: Classification Profile 시각적 비교 — `devlog/20260302_R02_tree_diff_visualization.md`
- **R05**: Assertion DB 0.1.8 vs 0.2.0 차이 분석 — `devlog/` 참조

## Next Tasks

**Roadmap:** `devlog/20260219_P63_future_roadmap.md`

### Data Quality

- ~~T-3a: Fill temporal_code~~ ✅ (84/85 done; 1 genus has no code in source)
- ~~T-3b: ?FAMILY genera~~ ✅ 32건 잠정 배정 완료 (parent_id 연결 + `questionable` opinion)
- **T-3c: Chinese romanization hyphens (~30)** — possible Wade-Giles; **deferred**
- ~~T-5: genus_locations country_id 수정 + Formation 오정렬~~ ✅
  - country_id: 3,769건 재매핑 (77.8%), 매칭률 95%+
  - Formation 오정렬: 350건 수정 (Type 1: 8, Type 2: 36, Type 3: 306)
  - 182개 orphan formation 레코드 정리

### Structural Improvements

- ~~T-1: Expand Taxonomic Opinions~~ ✅ 68 Uncertain families 전수 해소
  - Agnostina Suborder 추가 (id=5344, Agnostida 산하)
  - Agnostida 10개 Family → Agnostina 아래로 재배치 (관례적 배정, opinion 기록)
  - FAMILY UNCERTAIN 22건 → Suborder 연결 + `incertae_sedis` opinion
  - INDET 14건 → Trilobita 연결 + `indet` opinion
  - ?FAMILY/??FAMILY 32건 → Family 연결 + `questionable` opinion
  - Current: PLACED_IN 82 + SPELLING_OF 2 = **84 opinions**
  - assertion_status: `asserted` 13 / `incertae_sedis` 23 / `indet` 14 / `questionable` 32
- ~~T-4: Merge synonyms → taxonomic_opinions~~ ✅ 1,055 SYNONYM_OF opinions migrated
  - synonyms table → backward-compat VIEW; taxon_bibliography.synonym_id → opinion_id
  - synonym_type column added to taxonomic_opinions
  - 566 fide→bibliography links (433 migration + 133 post-fix); 154 unmatched fide in notes

### UI/Manifest

- ~~genus_detail 쿼리에 synonym JOIN 추가~~ ✅ genus_synonyms 쿼리 + 매니페스트 Synonymy 섹션
- ~~tree item 및 genera_table에 is_valid 컬럼 표시~~ ✅ boolean format, Yes/No label
- ~~`create_scoda.py --with-spa` 옵션 추가~~ ✅ `--with-spa` flag로 구현
- ~~`label_map` 동적 컬럼 label 지원~~ ✅ opinion_type별 동적 헤더 변경
- ~~Hub Manifest 자동 생성~~ ✅ `.scoda` 빌드 시 `{id}-{version}.manifest.json` 자동 생성
- ~~rank_detail Children 버그 수정~~ ✅ linked_table 전환, Genus redirect 지원
- ~~ui_queries pc.* prefix 수정~~ ✅ 7개 쿼리 수정, genus_locations country_id 3,750건 데이터 복원
- ~~genus_bibliography 쿼리 추가~~ ✅ FK 기반 참고문헌 연결
- ~~synonym manifest fix~~ ✅ genus_detail synonyms sub_query 추가, synonym_list → linked_table 전환
- ~~fide matching 개선~~ ✅ et al./year suffix/initial prefix 처리 → 133건 추가 매칭 (총 566건)

### P84: Tree Search 개선 + Watch 기능

- **Search Nodes 수정** — 검색창 기능 복구, 뷰포트 내 노드 팝업
- **Watch 기능** — 노드 우클릭 → Watch/Unwatch, Watch 목록 패널, 확대 렌더링(2×/1.5×)
- **Removed Taxa 목록** — Diff Tree/Animation에서 제거된 taxa 표시
- **상세**: `devlog/20260311_P84_tree_search_and_watch.md`

### Taxonomy Management (R01 로드맵)

- **Phase A: 최소 구조 보강** — `assertion.effective_year`, `reference.scope_type`, taxon opinion history UI
- **Phase B: Revision Package** — 논문 단위 assertion 일괄 import/review/accept 워크플로우
- **Phase C: Layered Profile** — profile layer 스택 + working classification

## Open Issues

- **1 unlinked synonym**: Szechuanella (syn 960) — preocc., not replaced (normal per NOTE 8)
- **257 parent_id NULL**: all invalid genera (normal) — valid genera **0건** (전수 해소)
- **1 valid genus without temporal_code**: Dignagnostus — no code in source (T-3a complete)
- **~30 Chinese romanization hyphens**: possible Wade-Giles notation, deferred (T-3c)
- Taxa without Location/Formation are all invalid taxa (normal)

## CI/CD

GitHub Actions workflows in `.github/workflows/`:

| Workflow | Trigger | Action |
|----------|---------|--------|
| `ci.yml` | push/PR to main | pytest 자동 실행 |
| `release.yml` | tag `v*.*.*` push | pytest → .scoda 빌드 → Hub Manifest 생성 → GitHub Release |
| `manual-release.yml` | workflow_dispatch | 수동 릴리스 (동일 파이프라인, hub manifest 포함) |
| `docs.yml` | push to main (docs/) | MkDocs 문서 사이트 빌드 → GitHub Pages 배포 |

**릴리스 방법:**
```bash
python scripts/build_trilobase_db.py    # DB 빌드
python scripts/validate_trilobase_db.py # 검증
python scripts/build_trilobase_scoda.py # .scoda 패키지 빌드
git add db/trilobase-0.3.1.db && git commit -m "release: v0.3.1"
git tag v0.3.1
git push origin main --tags
```

**주의:** scoda-engine 레포가 public이어야 CI에서 clone 가능 (private이면 deploy key/PAT 설정 필요)

## File Structure

```
trilobase/                                 # Domain data, scripts, and tests only
├── .github/workflows/                    # CI/CD (ci.yml, release.yml, manual-release.yml, docs.yml)
├── CLAUDE.md
├── HANDOFF.md                            # Current status + remaining tasks (this file)
├── CHANGELOG.md                          # Trilobase package changelog
├── CHANGELOG_paleocore.md                # PaleoCore package changelog
├── pytest.ini                             # pytest config (testpaths=tests)
├── requirements.txt                       # scoda-engine dependency
├── db/                                    # Canonical DBs (git tracked, versioned filenames)
│   ├── trilobase-0.3.0.db                # ★ 현재 메인 DB (assertion-centric)
│   ├── trilobase-canonical-0.2.6.db      # Legacy canonical DB (보존용)
│   ├── trilobase-assertion-*.db          # 이전 assertion DB 버전들 (보존용)
│   └── paleocore-0.1.1.db               # PaleoCore reference DB
├── dist/                                  # Build artifacts (gitignored)
│   ├── trilobase-{ver}.scoda             # .scoda package
│   ├── paleocore-{ver}.scoda
│   ├── *-{ver}.manifest.json             # Hub Manifest (SHA-256, 메타데이터)
│   └── *_overlay.db                      # Overlay DBs
├── data/                                  # Source data files
│   ├── sources/                          # ★ assertion DB 빌드 소스 (*.txt)
│   ├── trilobite_genus_list.txt          # Cleaned genus list (canonical version)
│   ├── trilobite_family_list.txt
│   ├── adrain2011.txt
│   ├── mcp_tools_trilobase.json          # MCP tool definitions
│   └── *.pdf                             # Reference PDFs
├── scripts/                               # ★ 활성 빌드 스크립트만 (60+ 레거시 → archive/)
│   ├── build_trilobase_db.py             # Trilobase DB 빌드 → db/
│   ├── build_trilobase_scoda.py          # trilobase.scoda → dist/
│   ├── validate_trilobase_db.py          # DB 검증 (17 checks)
│   ├── build_paleocore_db.py             # PaleoCore DB → db/
│   ├── build_paleocore_scoda.py          # paleocore.scoda → dist/
│   ├── build_all.py                      # 전체 빌드 (DB + .scoda)
│   ├── convert_to_source_format.py       # data/sources/*.txt 재생성
│   ├── db_path.py                        # DB 경로 헬퍼 (find_trilobase_db 등)
│   └── archive/                          # 레거시 스크립트 보관
├── tests/
│   ├── conftest.py                       # Shared fixtures
│   └── test_trilobase.py                # Trilobase domain tests (118)
├── vendor/                               # Third-party reference data
├── design/                               # Design & concept documents
├── docs/                                 # MkDocs documentation site (EN/KO)
│   ├── canonical_vs_assertion.md         # 두 DB 구조 비교 설명
│   └── source_data_guide.md              # 소스 데이터 작성 가이드
└── devlog/                               # 작업 기록

scoda-engine/                              # Separate repo: /mnt/d/projects/scoda-engine
├── pyproject.toml                         # pip install -e ".[dev]"
├── scoda_engine/                          # SCODA runtime package
│   ├── scoda_package.py, app.py, mcp_server.py, gui.py, serve.py
│   ├── entity_schema.py, crud_engine.py   # P80: manifest-driven CRUD
│   ├── templates/, static/
├── tests/                                 # Runtime tests (218 + 27 CRUD)
└── scripts/                               # build.py, release.py, etc.
```

## Test Status

### Trilobase (this repo)

| File | Tests | Status |
|------|-------|--------|
| `tests/test_trilobase.py` | 118 | ✅ Passing |

### scoda-engine (separate repo)

| File | Tests | Status |
|------|-------|--------|
| `tests/test_runtime.py` | 218 | ✅ Passing |
| `tests/test_crud.py` | 27 | ✅ Passing |
| `tests/test_mcp.py` | 6 | ✅ 1 / ⚠ 5 (requires .scoda in CWD) |
| `tests/test_mcp_basic.py` | 1 | ✅ Passing |

**How to run:**
```bash
# Trilobase
pip install -e /mnt/d/projects/scoda-engine[dev]
pytest tests/

# scoda-engine
cd /mnt/d/projects/scoda-engine
pip install -e ".[dev]"
pytest tests/
```

**pytest config (`pytest.ini`):**
- `testpaths = tests` — test directory
- `asyncio_mode = auto` — auto-detect async tests
- `asyncio_default_fixture_loop_scope = function` — isolated event loops

## DB Schema

### Trilobase DB (trilobase-0.3.0.db)

```sql
-- taxon: 5,627 records — all taxa (Class~Genus + Subfamily + placeholders)
taxon (
    id, name, rank, author, year, year_suffix,
    type_species, type_species_author, formation, location, family,
    temporal_code, is_valid, notes, raw_entry, created_at
)

-- assertion: 8,382 records — PLACED_IN 7,305 + SYNONYM_OF 1,075 + SPELLING_OF 2
assertion (
    id, subject_taxon_id, predicate, object_taxon_id, value_text,
    reference_id, assertion_status, curation_confidence,
    synonym_type, notes, created_at
)

-- reference: 2,135 records
reference (id, authors, year, year_suffix, title, journal, volume, pages,
           publisher, city, editors, book_title, reference_type, raw_entry)

-- classification_profile: 3 records (default, treatise1959, treatise2004)
classification_profile (id, name, description, created_at)

-- classification_edge_cache: 8,930 records
classification_edge_cache (profile_id, taxon_id, parent_taxon_id)

-- genus_formations: 4,503 records
genus_formations (id, genus_id, formation_id, is_type_locality, notes)

-- genus_locations: 4,849 records
genus_locations (id, genus_id, country_id, region, is_type_locality, notes)

-- taxon_reference: 4,173 records
taxon_reference (id, taxon_id, reference_id, relationship_type,
                 assertion_id, match_confidence, match_method, notes, created_at)

-- Views
synonyms         -- backward-compat VIEW over assertion WHERE predicate='SYNONYM_OF'
v_taxonomy_tree  -- edge_cache 기반 트리 뷰
v_taxonomic_ranks -- edge_cache 기반 랭크 뷰

-- SCODA tables
artifact_metadata, provenance, schema_descriptions,
ui_display_intent, ui_queries (46), ui_manifest (1)
```

**SQLite ATTACH usage (3-DB):**
```python
conn = sqlite3.connect('db/trilobase-0.3.0.db')
conn.execute("ATTACH DATABASE 'dist/trilobase_overlay.db' AS overlay")
conn.execute("ATTACH DATABASE 'db/paleocore-0.1.1.db' AS pc")
```

## Notes

- `data/sources/*.txt`가 assertion DB 빌드의 정규 소스
- `db/trilobase-0.3.0.db`가 현재 메인 DB (`scripts/db_path.py:find_trilobase_db()`로 resolve)
- `db/trilobase-canonical-0.2.6.db`는 이전 canonical DB (taxonomic_ranks 기반, 보존용)
- Original PDF reference: Jell & Adrain (2002)
