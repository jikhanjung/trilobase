# Trilobase Project Handover

**Last updated:** 2026-03-09

## Project Overview

A trilobite taxonomic database project. Genus data extracted from Jell & Adrain (2002) PDF is cleaned, normalized, and distributed as a SCODA package.

- **SCODA Engine** (runtime): separate repo at `/mnt/d/projects/scoda-engine` (`pip install -e /mnt/d/projects/scoda-engine[dev]`)
- **Completed Phase 1~46 details**: see [HISTORY.md](design/HISTORY.md)

## Current Status

| Item | Value |
|------|-------|
| Phases completed | 1~46 (all done) |
| Trilobase version | 0.2.6 |
| PaleoCore version | 0.1.1 |
| taxonomic_ranks | 5,341 records (Class~Genus + 2 placeholders + 1 Suborder) |
| Valid genera | 4,259 (83.3%) |
| Invalid genera | 856 (16.7%) |
| Valid genera parent_id NULL | 0 (was 68, all resolved) |
| Synonym linkage | 99.9% (1,054/1,055) |
| Taxonomic opinions | 1,139 (PLACED_IN 82 + SPELLING_OF 2 + SYNONYM_OF 1,055) |
| Tests | 118 passing |

## Database Status

**Canonical DB (trilobase-{version}.db) — read-only, immutable:**

| Table/View | Records | Description |
|------------|---------|-------------|
| taxonomic_ranks | 5,341 | Unified taxonomy (Class~Genus) + 2 placeholders + 1 Suborder |
| synonyms (view) | 1,055 | Backward-compat VIEW over taxonomic_opinions SYNONYM_OF |
| genus_formations | 4,503 | Genus-Formation many-to-many |
| genus_locations | 4,849 | Genus-Country many-to-many |
| bibliography | 2,130 | Literature Cited references |
| taxon_bibliography | 4,173 | Taxon↔Bibliography FK links (opinion_id replaces synonym_id) |
| taxonomic_opinions | 1,139 | All opinions (PLACED_IN 82 + SPELLING_OF 2 + SYNONYM_OF 1,055) |
| taxa (view) | 5,113 | Backward-compatibility view |
| artifact_metadata | 7 | SCODA artifact metadata |
| provenance | 5 | Data provenance |
| schema_descriptions | 112 | Table/column descriptions |
| ui_display_intent | 6 | SCODA view type hints |
| ui_queries | 38 | Named SQL queries |
| ui_manifest | 1 | Declarative view definitions (JSON) |

**Overlay DB (trilobase_overlay.db) — read/write, user-local data:**

| Table | Records | Description |
|-------|---------|-------------|
| overlay_metadata | 2 | Canonical DB version tracking (canonical_version, created_at) |
| user_annotations | 0 | User annotations (Local Overlay) |

## Modular Rebuild Pipeline (P72/P73) ✅

소스 텍스트 2개로부터 현재 DB와 동일한 결과를 한 번에 생성하는 모듈화된 파이프라인.
기존 46개 Phase + 10+ fix 스크립트의 모든 교훈을 통합.

```bash
python scripts/rebuild_database.py --output-dir dist/rebuild/ --validate
# → dist/rebuild/trilobase.db + dist/rebuild/paleocore.db
# → 35/35 validations passed
```

**Pipeline 모듈**: `scripts/pipeline/` (clean → hierarchy → parse_genera → load_data → paleocore → junctions → metadata → validate)

**주요 개선**: is_valid 정확도 (s.o.s.=VALID, suppressed anywhere, NOTE 8), Type 3 formation→region (356건), synonym dedup, bibliography dot-optional, hierarchy footnote stripping

**P73 차이 해소**: SYNONYM_OF 행 단위 diff 0건 달성. hierarchy 파싱(3노드), SPELLING_OF 매핑(47속), synonym 추출(~13건), Type 3 reclassification(356건), bracket stripping(5속) 수정.

**상세**: `devlog/20260228_099_rebuild_pipeline_complete.md`, `devlog/20260228_100_rebuild_diff_resolution.md`

## P74: Assertion-Centric Test DB ✅

Canonical DB 변경 없이, assertion-centric 모델을 별도 테스트 DB로 구현.

```bash
python scripts/create_assertion_db.py   # → db/trilobase-assertion-{version}.db
python scripts/validate_assertion_db.py  # → 15/15 checks passed
```

| 테이블 | 건수 | 설명 |
|--------|------|------|
| `taxon` | 5,391 | parent_id 제거 (+50 Treatise taxa) |
| `reference` | 2,134 | bibliography + JA2002 (id=2132) + Treatise ch4/ch5 |
| `assertion` | 6,563 | PLACED_IN 5,506 + SYNONYM_OF 1,055 + SPELLING_OF 2 |
| `classification_profile` | 3 | default, ja2002_strict, treatise2004 |
| `classification_edge_cache` | 10,221 | default (5,083) + treatise2004 (5,138) |
| `ui_queries` | 45 | +taxonomy_tree_genera_counts, classification_profiles_selector |

Views: `v_taxonomy_tree`, `v_taxonomic_ranks`, `synonyms` (기존 호환)

**상세**: `devlog/20260228_P74_assertion_centric_plan.md`

## P76: Radial Tree → Canonical trilobase.scoda ✅

P75에서 assertion DB 전용이던 Radial Tree를 canonical `trilobase.scoda`에도 추가.
`taxonomic_ranks`에 `parent_id`가 이미 있으므로 별도 edge 쿼리 없이 쿼리 1개 + manifest 뷰 1개만 추가.

- `radial_tree_nodes` 쿼리: valid Genus 포함 (invalid 제외), parent_id 직접 반환
- `radial_tree` manifest 뷰: `display: "radial"`, `rank_radius` 동심원 배치
- ui_queries: 37 → 38, manifest views: 13 → 14 (7 tab + 7 detail)

**상세**: `devlog/20260301_P76_radial_tree_canonical_scoda.md`

## P77: Versioned DB Filename ✅

모든 canonical DB를 `{name}-{version}.db` 패턴으로 통일. 파일명만으로 DB 버전 식별 가능.

- `scripts/db_path.py`: `find_trilobase_db()`, `find_assertion_db()`, `find_paleocore_db()` glob 헬퍼
- 활성 스크립트 + 테스트 DB_PATH 교체 (`find_*_db()` 사용)
- assertion DB: `dist/assertion_test/` → `db/` 이동, 파일명 `trilobase-assertion-{ver}.db`
- `bump_version.py`: 버전 범프 시 기존 파일 복사(copy)하여 과거 버전 보존 (trilobase, paleocore 공통)
- CI workflow: 별도 "Build assertion DB" step 제거, release artifact는 `dist/*.scoda`만 포함
- `.scoda` 패키지 영향 없음 (내부에서 `data.db`로 저장)

**상세**: `devlog/20260301_P77_versioned_db_filename.md`

## P78: Treatise (2004) Taxonomy Import ✅

Treatise on Invertebrate Paleontology (2004) Agnostida (ch4) + Redlichiida (ch5) 분류를 제3의 의견 소스로 assertion DB에 추가.

```bash
python scripts/create_assertion_db.py      # 기존대로 assertion DB 생성
python scripts/import_treatise.py          # Treatise 데이터 증분 추가
python scripts/validate_treatise_import.py # 17/17 검증 통과
python scripts/validate_assertion_db.py    # 15/15 검증 통과
```

| 항목 | 수량 |
|------|------|
| Treatise references | 2 (ch4: Shergold et al., ch5: Palmer & Repina) |
| 신규 taxon | 50 (Subfamily 32, Superfamily 3, Family 4, Genus 3, placeholder 8) |
| PLACED_IN assertions | 421 (asserted 367, questionable 17, incertae_sedis 27, indet 10) |
| treatise2004 프로필 edges | 5,138 (default 5,083 + Subfamily 계층) |

**주요 결정:**
- Eodiscida (id=2) 재사용: Treatise에서 Agnostida 하위 Suborder로 배치
- Agnostida → Trilobita: Treatise 프로필에서 포함
- Hybrid edge cache: default 유지 + Treatise가 명시한 taxa만 교체
- Subfamily rank 신규 추가 (32건), radial tree rank_radius 7단계로 확장
- 모든 Treatise assertion은 `is_accepted=0` (default 프로필 영향 없음)

**상세**: `devlog/20260301_105_P78_treatise_import.md`

## P79: Profile-Based Taxonomy Tree + Profile Selector UI ✅

P78 Treatise import 후 orphan 문제 해결: `classification_edge_cache` 기반으로 tree 표시, profile selector UI 추가.

**scoda-engine 변경:**
- `app.js`: `globalControls` state, `renderGlobalControls()`, `fetchQuery()` global params 자동 병합, `isLeaf` 확장
- `tree_chart.js` (was `radial.js`): `$variable` reference 해석 (`$profile_id` → globalControls 값)
- `index.html`: `#global-controls` 컨테이너
- `style.css`: compact select 스타일

**trilobase 변경:**
- `create_assertion_db.py`: 4개 쿼리 → edge_cache 기반, `classification_profiles_selector` 추가, `global_controls` manifest, version 0.1.2
- Profile 1 (default): 224 tree nodes, Profile 3 (treatise2004): 272 tree nodes

**상세**: `devlog/20260301_106_P79_profile_selector_ui.md`

## P80: Assertion DB CRUD (Manifest-Driven Editing) ✅

scoda-engine에 manifest-driven CRUD 프레임워크를 추가하고 assertion DB에 적용. Admin 모드에서 웹 UI를 통해 taxon/assertion/reference/classification_profile CRUD 가능.

**scoda-engine 신규 파일:**
- `scoda_engine/entity_schema.py`: `FieldDef`, `EntitySchema` 데이터클래스 + 파서/검증
- `scoda_engine/crud_engine.py`: 제네릭 CRUD 엔진 (FK 검증, unique 제약, post-mutation 훅)
- `tests/test_crud.py`: 27개 CRUD 테스트

**scoda-engine 수정:**
- `serve.py`: `--db-path`, `--mode admin|viewer` CLI 인자
- `app.py`: REST 엔드포인트 10개 (`/api/entities/*`, `/api/search/*`), admin 가드
- `app.js`: Admin UI (Edit/Delete/Add 버튼, FK autocomplete, readonly_on_edit, PLACED_IN rank 필터)
- `validate_manifest.py`: `editable_entities` 검증 규칙

**trilobase 변경:**
- `create_assertion_db.py`: `editable_entities` 선언 (taxon, assertion, reference, classification_profile), linked_table 인라인 CRUD, JA2002 ref id=0 → auto_increment(2132)
- `test_trilobase.py`: +6 editable_entities 검증 테스트

```bash
# Admin 모드로 실행
python -m scoda_engine.serve --db-path db/trilobase-assertion-0.1.3.db --mode admin --port 8090
```

**상세**: `devlog/20260301_107_P80_assertion_crud.md`

## Assertion DB v0.1.5: Treatise 1959 + Profile Comparison ✅

### Treatise 1959 Import (devlog 109)
1959 Treatise on Invertebrate Paleontology Part O에서 삼엽충 전체 분류 체계를 추출하여 `treatise1959` 프로필로 import.

- OCR + 수동 입력 → 8 orders, 13 suborders, 33 superfamilies, 142 families, 128 subfamilies, 1,014 genera
- `treatise1959` 프로필: standalone 1,324 edges
- `treatise2004` 프로필: treatise1959 기반 1,667 edges (Agnostida/Redlichiida 교체)

**상세**: `devlog/20260307_109_treatise1959_import.md`, `devlog/20260307_110_assertion_v015_profile_fixes.md`

### Profile Diff Table — R02 Phase 0+1 (devlog 111)
Compare 모드 UI 인프라 + Diff Table 구현.
- `compare_profile_id` global control, Compare 모드 자동 토글
- `profile_diff` SQL 쿼리: moved/added/removed 행 색상 코딩

**상세**: `devlog/20260307_111_profile_diff_table.md`

### Side-by-Side Tree — R02 Phase 3 (devlog 112~113)
`tree_chart.js`를 `TreeChartInstance` 클래스로 리팩토링하여 듀얼 렌더링 구현.

- 전역 변수 20+개 → 인스턴스 멤버, 전역 함수 30+개 → 클래스 메서드
- `loadSideBySideView()`: 좌(base profile) / 우(compare profile) 독립 렌더링
- 동기화 5종: zoom/pan, layout mode, hover highlight, depth toggle, collapse/expand, view-as-root
- 양쪽 독립 tooltip
- 성능 최적화: offscreen bitmap cache (zoom), SVG 라벨 숨김, guide depth 캐싱
- scoda-engine v0.2.0 (TreeChartInstance 리팩토링)

**상세**: `devlog/20260307_112_side_by_side_tree.md`, `devlog/20260307_113_sbs_sync_and_perf.md`

## Assertion DB v0.1.6: Profile Comparison Compound View + Morphing ✅

3개의 개별 compare 뷰(Diff Table, Diff Tree, Side-by-Side)를 하나의 **Profile Comparison** compound view로 통합하고, **Morphing** 애니메이션 뷰 추가.

### Compound View
- `compound` view 타입: sub-view 탭(Diff Table, Diff Tree, Side-by-Side, Morphing)으로 구성
- 자체 From/To profile selector 보유, 기존 global `compare_profile_id` 제거
- `tree_chart_morph` display 타입 신규 추가

### Morphing 애니메이션 (R02 Phase 4)
- `loadMorph()` → `renderMorphFrame(t)` → `startMorphAnimation()` 파이프라인
- Transport controls: |< ◀ || ▶ >| + scrubber + speed 조절
- 정방향/역방향 재생, 현재 위치에서 이어 재생
- Radial/Rectangular 양쪽 지원, view-as-root 중에도 작동

### 렌더링 단순화 + 성능 개선
- SVG label → canvas `drawLabels()` 전환, bitmap cache/depth toggle/동적 radius 제거
- `textScale`: A−/A+ 버튼으로 font/node 크기 직접 조절 (layout 재계산 불필요)
- `taxonomy_tree` genera_count 쿼리: 10,310ms → 9ms (per-row recursive CTE → 별도 flat 쿼리 + JS 전파)
- Rectangular tree depth spacing: view-as-root 시 rank 수 × depthSpacing 기반으로 수정

### 기타 UI
- Global loading indicator (animated gradient bar + wait cursor)
- Show Text / Hide Text 토글 (탭 바)
- Radial tree fit margin 10% 추가

**상세**: `devlog/20260309_115_compound_view_and_morphing.md`

## R01/R02: 설계 리뷰 문서

### R01: 시간에 따라 변화하는 Taxonomy 관리 방법

Assertion-centric 모델의 확장 방향을 탐색한 아이디어 문서:
- **Layered Profile**: profile을 여러 layer의 스택으로 구성 (부분 개정 논문 반영)
- **Assertion Timeline**: 개별 taxon의 의견 이력 추적 (`supersedes_id`)
- **Revision Package**: 논문 단위 assertion 일괄 import/revert 워크플로우
- **Working Classification**: 사용자의 현행 분류를 관리하는 mutable profile
- **단계적 접근 제안**: Phase A (최소 구조 보강) → B (Revision Package) → C (Layered Profile) → D (Tree Editing)

**상세**: `devlog/20260302_R01_taxonomy_management.md`

### R02: 두 Classification Profile의 시각적 비교

Profile 간 차이를 시각화하는 구체적 설계 문서:
- **Compare UI**: 패턴 A (Compare 모드 토글) 채택
- **표시 모드 4가지**: Diff Table → Diff Tree → Overlay + Side-by-side → Animated Morphing
- **구현 순서**: Phase 0 (Compare UI 인프라) → 1 (Diff Table) → 2 (Diff Tree) → 3 (Overlay/Side-by-side) → 4 (Morphing)
- **책임 분리**: scoda-engine = "어떻게 비교하고 그릴지", trilobase = "무엇을 비교할지" (manifest 계약)

**상세**: `devlog/20260302_R02_tree_diff_visualization.md`

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

### Assertion DB — Profile Comparison (R02 로드맵)

- ~~Phase 0: Compare UI 인프라~~ ✅ (devlog 111)
- ~~Phase 1: Diff Table~~ ✅ (devlog 111)
- ~~Phase 2: Diff Tree~~ ✅ (devlog 114) — diff 색상 코딩 (moved/added/removed)
- ~~Phase 3: Side-by-side~~ ✅ (devlog 112~113) — 동기화 5종 + 성능 최적화 포함
- ~~Phase 4: Animated Morphing~~ ✅ (devlog 115) — transport controls, scrubber, 정방향/역방향 재생

### Assertion DB — Taxonomy Management (R01 로드맵)

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
python scripts/bump_version.py trilobase 0.2.7
# → db/trilobase-0.2.6.db 보존, db/trilobase-0.2.7.db 생성
git add db/trilobase-0.2.7.db && git commit -m "release: v0.2.7"
git tag v0.2.7
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
│   ├── trilobase-{ver}.db                 # Trilobase SQLite DB
│   ├── trilobase-assertion-{ver}.db       # Assertion-centric DB
│   └── paleocore-{ver}.db                 # PaleoCore reference DB
├── dist/                                  # Build artifacts (gitignored)
│   ├── trilobase-{ver}.scoda              # .scoda package (버전 포함 파일명)
│   ├── paleocore-{ver}.scoda
│   ├── *-{ver}.manifest.json              # Hub Manifest (SHA-256, 메타데이터)
│   └── *_overlay.db                       # Overlay DBs
├── data/                                  # Source data files
│   ├── trilobite_genus_list.txt           # Cleaned genus list (canonical version)
│   ├── trilobite_genus_list_original.txt
│   ├── trilobite_family_list.txt
│   ├── trilobite_nomina_nuda.txt
│   ├── adrain2011.txt
│   ├── mcp_tools_trilobase.json           # MCP tool definitions
│   └── *.pdf                              # Reference PDFs
├── spa/                                   # Reference Implementation SPA (trilobase-specific)
│   └── index.html                        # Single-file SPA (HTML+CSS+JS, 2,915 lines)
├── scripts/                               # Domain pipeline scripts
│   ├── rebuild_database.py                # ★ Modular rebuild orchestrator (P72)
│   ├── pipeline/                          # ★ Modular rebuild pipeline modules
│   │   ├── clean.py                       #   Step 1: text loading
│   │   ├── hierarchy.py                   #   Step 2: adrain2011 hierarchy
│   │   ├── parse_genera.py                #   Step 3: genus entry parsing
│   │   ├── load_data.py                   #   Step 4: schema + data load
│   │   ├── paleocore.py                   #   Step 5: PaleoCore DB
│   │   ├── junctions.py                   #   Step 6: junction tables
│   │   ├── metadata.py                    #   Step 7: SCODA metadata
│   │   └── validate.py                    #   Step 8: validation (35 checks)
│   ├── create_scoda.py                    # trilobase.scoda → dist/ (--with-spa 옵션, hub manifest 자동 생성)
│   ├── create_paleocore_scoda.py          # paleocore.scoda → dist/
│   ├── create_paleocore.py                # PaleoCore DB → db/
│   ├── bump_version.py                    # Version bump script
│   ├── add_opinions_schema.py             # Taxonomic opinions migration
│   ├── add_spelling_of_opinions.py        # SPELLING_OF opinion type
│   ├── migrate_synonyms_to_opinions.py    # T-4: synonyms → SYNONYM_OF opinions
│   ├── restructure_agnostida_opinions.py  # Agnostida order-level opinions
│   ├── fix_country_id.py                  # T-5: country_id 일괄 수정
│   ├── fix_formation_misalignment.py      # T-5: formation 오정렬 수정
│   ├── fill_temporal_codes.py             # temporal_code auto-fill from raw_entry
│   ├── link_bibliography.py               # taxon_bibliography link builder
│   ├── create_assertion_db.py              # P74/P80: assertion-centric DB → db/ (with editable_entities)
│   ├── validate_assertion_db.py            # P74: assertion DB validation (12 checks)
│   ├── create_database.py                 # DB creation → db/
│   └── ... (normalize, import, etc.)
├── tests/
│   ├── conftest.py                        # Shared fixtures
│   └── test_trilobase.py                  # Trilobase domain tests (118)
├── vendor/
│   ├── cow/v2024/States2024/statelist2024.csv
│   └── ics/gts2020/chart.ttl
├── design/                               # Design & concept documents
│   ├── HISTORY.md                         # Completed Phase 1~46 detailed records
│   ├── paleocore_schema.md
│   ├── scoda_package_architecture.md
│   ├── scoda_registry_architecture.md
│   └── scoda_registry_dependency_distribution_detailed.md
├── docs/                                  # MkDocs documentation site (EN/KO)
│   ├── index.en.md / index.ko.md
│   ├── getting-started.en.md / .ko.md
│   ├── database/                          # Schema, queries, PaleoCore
│   ├── architecture/                      # SCODA package & registry
│   ├── api/                               # MCP tools reference
│   └── project/                           # Changelog, handoff, history
└── devlog/

scoda-engine/                              # Separate repo: /mnt/d/projects/scoda-engine
├── pyproject.toml                         # pip install -e ".[dev]"
├── scoda_engine/                          # SCODA runtime package
│   ├── scoda_package.py, app.py, mcp_server.py, gui.py, serve.py
│   ├── entity_schema.py, crud_engine.py   # P80: manifest-driven CRUD
│   ├── templates/, static/
├── tests/                                 # Runtime tests (218 + 27 CRUD)
├── scripts/                               # build.py, release.py, etc.
├── examples/, docs/
└── ScodaDesktop.spec
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

### Canonical DB (trilobase-{ver}.db)

```sql
-- taxonomic_ranks: 5,341 records — unified taxonomy (Class~Genus) + 2 placeholders + Agnostina Suborder
taxonomic_ranks (
    id, name, rank, parent_id, author, year, year_suffix,
    genera_count, notes, created_at,
    -- Genus-specific fields
    type_species, type_species_author, formation, location, family,
    temporal_code, is_valid, raw_entry
)

-- synonyms: backward-compat VIEW over taxonomic_opinions WHERE opinion_type = 'SYNONYM_OF'
-- Returns: id, junior_taxon_id, senior_taxon_name, senior_taxon_id,
--          synonym_type, fide_author, fide_year, notes

-- genus_formations: 4,853 records — Genus-Formation many-to-many
genus_formations (id, genus_id, formation_id, is_type_locality, notes)

-- genus_locations: 4,841 records — Genus-Country many-to-many
genus_locations (id, genus_id, country_id, region, is_type_locality, notes)

-- bibliography: 2,130 records — Literature Cited references
bibliography (id, authors, year, year_suffix, title, journal, volume, pages,
              publisher, city, editors, book_title, reference_type, raw_entry)

-- taxon_bibliography: 4,173 records — Taxon↔Bibliography FK links
taxon_bibliography (id, taxon_id, bibliography_id, relationship_type,
                    opinion_id, match_confidence, match_method, notes, created_at)

-- taxonomic_opinions: 1,139 records — all opinions (PLACED_IN 82, SPELLING_OF 2, SYNONYM_OF 1,055)
taxonomic_opinions (id, taxon_id, opinion_type, related_taxon_id, proposed_valid,
                    bibliography_id, assertion_status, curation_confidence,
                    is_accepted, synonym_type, notes, created_at)
-- Triggers: trg_deactivate_before_insert, trg_sync_parent_insert,
--           trg_deactivate_before_update, trg_sync_parent_update

-- taxa: backward-compatibility view
CREATE VIEW taxa AS SELECT ... FROM taxonomic_ranks WHERE rank = 'Genus';

-- SCODA-Core tables
artifact_metadata (key, value)                    -- artifact metadata (key-value)
provenance (id, source_type, citation, description, year, url)  -- data provenance
schema_descriptions (table_name, column_name, description)      -- schema descriptions

-- SCODA UI tables
ui_display_intent (id, entity, default_view, description, source_query, priority)  -- view hints
ui_queries (id, name, description, sql, params_json, created_at)                   -- named queries
ui_manifest (name, description, manifest_json, created_at)                         -- declarative view defs (JSON)

-- Note: 8 PaleoCore tables were DROPped in Phase 34
-- countries, formations, geographic_regions, cow_states, country_cow_mapping,
-- temporal_ranges, ics_chronostrat, temporal_ics_mapping → paleocore.db (pc.* prefix)
```

### Overlay DB (trilobase_overlay.db)

```sql
-- overlay_metadata: canonical DB version tracking
overlay_metadata (key, value)  -- canonical_version, created_at

-- user_annotations: user annotations
user_annotations (
    id, entity_type, entity_id, entity_name,  -- entity_name: cross-release matching
    annotation_type, content, author, created_at
)
```

**SQLite ATTACH usage (3-DB):**
```python
conn = sqlite3.connect('db/trilobase-0.2.6.db')  # Canonical DB (versioned)
conn.execute("ATTACH DATABASE 'dist/trilobase_overlay.db' AS overlay")
conn.execute("ATTACH DATABASE 'db/paleocore-0.1.1.db' AS pc")

# Canonical tables: SELECT * FROM taxonomic_ranks
# Overlay tables:   SELECT * FROM overlay.user_annotations
# PaleoCore tables: SELECT * FROM pc.countries
# Cross-DB JOIN:    SELECT ... FROM genus_locations gl JOIN pc.countries c ON gl.country_id = c.id
```

## DB Usage Examples

```bash
# Basic query (using taxa view)
sqlite3 db/trilobase-0.2.6.db "SELECT * FROM taxa LIMIT 10;"

# Full hierarchy query
sqlite3 db/trilobase-0.2.6.db "SELECT g.name, f.name as family, o.name as 'order'
FROM taxonomic_ranks g
LEFT JOIN taxonomic_ranks f ON g.parent_id = f.id
LEFT JOIN taxonomic_ranks sf ON f.parent_id = sf.id
LEFT JOIN taxonomic_ranks o ON sf.parent_id = o.id
WHERE g.rank = 'Genus' AND g.is_valid = 1 LIMIT 10;"

# Genus formations (using relation table)
sqlite3 db/trilobase-0.2.6.db "SELECT g.name, f.name as formation
FROM taxonomic_ranks g
JOIN genus_formations gf ON g.id = gf.genus_id
JOIN formations f ON gf.formation_id = f.id
WHERE g.name = 'Paradoxides';"

# Genera by country (using relation table)
sqlite3 db/trilobase-0.2.6.db "SELECT g.name, gl.region
FROM taxonomic_ranks g
JOIN genus_locations gl ON g.id = gl.genus_id
JOIN countries c ON gl.country_id = c.id
WHERE c.name = 'China' LIMIT 10;"
```

## Notes

- `data/trilobite_genus_list.txt` is always the canonical text version
- `db/trilobase-{ver}.db` is the latest database (use `scripts/db_path.py:find_trilobase_db()` to resolve)
- Git commit after each Phase completion
- Original PDF reference: Jell & Adrain (2002)
