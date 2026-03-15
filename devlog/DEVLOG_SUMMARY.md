# Trilobase Devlog Summary

**기간**: 2026-02-19 ~ 2026-03-15
**총 파일 수**: 87개 (작업 로그 51개 · 계획 문서 26개 · 리뷰 문서 5개 · 기타 5개)
**최종 갱신**: 2026-03-15

---

## 목차

1. [날짜별 작업 내역](#날짜별-작업-내역)
2. [주제별 그룹](#주제별-그룹)
3. [테스트 수 이력](#테스트-수-이력)
4. [버전 이력](#버전-이력)
5. [통계](#통계)

---

## 날짜별 작업 내역

### 2026-02-19

| 번호/코드 | 제목 | 요약 |
|-----------|------|------|
| P62 | repo_split_scoda_engine | scoda-engine을 별도 레포로 분리하는 계획. `scoda_desktop` → `scoda_engine` 모듈 이름 변경 및 pip install 의존성 방식 설계. |
| 078 | repo_split_scoda_engine | scoda-engine 레포 분리 완료. trilobase는 pip install -e 방식으로 scoda-engine에 의존. 테스트 66개 통과. |
| 079 | db_dist_reorganization | .db 파일 → `db/`, .scoda 패키지 → `dist/`로 디렉토리 구조 재편. 23개 스크립트 경로 업데이트. |
| P63 | future_roadmap | T-1(Uncertain Family Opinions), T-2(Assertion-Centric 모델), T-3(데이터 품질 잔여 과제) 로드맵 계획. |
| 080 | fix_null_parent_13_genera | raw_entry에 유효 Family가 있으나 파싱 실패로 parent_id가 NULL인 13개 속 수정. |
| 081 | fix_unlinked_synonyms | 연결되지 않은 동의어 24건 수정 → 잔여 1건(Szechuanella, 의도적). 동의어 연결률 99.9%. |
| 082 | data_quality_fixes | BRAÑA 인코딩 13건, Paraacidaspis 중복, 콜론 Family 4건, PDF 하이픈 165건, 공백 44건 등 대규모 데이터 품질 수정. |

### 2026-02-20

| 번호/코드 | 제목 | 요약 |
|-----------|------|------|
| P64 | taxon_bibliography | taxon과 bibliography를 연결하는 junction table 설계 계획. author/year 매칭 방식 및 신뢰도 기준 설계. |
| 083 | taxon_bibliography_junction | `taxon_bibliography` junction table 구현. 4,040건 고신뢰도 링크(original_description 3,607 + fide 433). 테스트 82개 통과. |

### 2026-02-21

| 번호/코드 | 제목 | 요약 |
|-----------|------|------|
| 084 | null_parent_families_to_order_uncertain | 부모 없는 Family 25건을 Order Uncertain(id=144) 하위로 이동. |
| P65 | version_changelog_process | CHANGELOG.md와 버전 관리 스크립트(`bump_version.py`) 도입 계획. |
| 085 | version_changelog_process | CHANGELOG.md 생성, bump_version.py 작성. trilobase 0.2.0, paleocore 0.1.1 버전 발행. |

### 2026-02-22

| 번호/코드 | 제목 | 요약 |
|-----------|------|------|
| P66a | group_a_fix_and_agnostida | Agnostida Order 신설 및 그룹A 데이터 수정 계획. |
| P66b | spelling_of_opinion_type | SPELLING_OF opinion 타입 추가 계획. |
| 086 | group_a_fix_and_agnostida | 철자 변이 중복 3건 수정; Agnostida Order를 PLACED_IN opinions으로 신설(10개 Family). 테스트 92개 통과. |
| 087 | spelling_of_and_agnostida_restructure | SPELLING_OF opinion 타입 추가; Dokimocephalidae/Chengkouaspidae placeholder 추가; temporal code 84건 보완. 테스트 100개 통과. |
| 088 | parent_id_null_resolution | 유효 속 68건의 NULL parent_id 전량 해소; Agnostina Suborder 신설; assertion_status 타입(incertae_sedis, questionable, indet) 84건 추가. 테스트 100개 통과. |
| P67 | scoda_spec_sync | SCODA 명세 문서를 구현 실제와 동기화 (checksum, 의존성 버전 범위, 필수 필드). |

### 2026-02-23

| 번호/코드 | 제목 | 요약 |
|-----------|------|------|
| 089 | label_map_dynamic_column | manifest 컬럼에 `label_map` 기능 추가 — opinion_type 값에 따라 헤더 라벨 동적 교체. 테스트 101개 통과. |
| P68 | ci_cd_github_actions | GitHub Actions CI/CD 파이프라인 설계 계획(ci.yml, release.yml, manual-release.yml). |
| 090 | ci_cd_implementation | GitHub Actions CI(ci.yml) + tag-triggered release.yml + manual-release.yml 구현 완료. |
| 091 | ui_query_manifest_improvements | bibliography_genera를 FK 기반 쿼리로 전환; genus_bibliography 쿼리 추가; genus_detail에 linked_table 섹션 3개 추가. |

### 2026-02-24

| 번호/코드 | 제목 | 요약 |
|-----------|------|------|
| 092 | rank_detail_children_fix | Children 테이블 렌더링 버그(type rank_children → linked_table) 수정; rank_detail → genus_detail 리다이렉트 추가. 테스트 101개 통과. |
| 093 | query_fixes_and_data_cleanup | 7개 쿼리의 pc.* prefix 오류 수정; 3,750건 genus_locations country_id 오류 수정. 테스트 101개 통과. |

### 2026-02-25

| 번호/코드 | 제목 | 요약 |
|-----------|------|------|
| 094 | hub_manifest_generation | .scoda 패키지 생성 시 `.manifest.json` Hub 레지스트리 파일을 함께 생성하는 `generate_hub_manifest()` 추가. |
| 095 | manual_release_manifest_fix | manual-release.yml에서 `dist/*.manifest.json` 누락 수정. |

### 2026-02-26

| 번호/코드 | 제목 | 요약 |
|-----------|------|------|
| P69 | mkdocs_documentation_site | MkDocs + Material + i18n 기반 GitHub Pages 문서 사이트 계획 (이 세션에서 미구현). |

### 2026-02-27

| 번호/코드 | 제목 | 요약 |
|-----------|------|------|
| P70 | synonym_migration_plan | `synonyms` 테이블을 `taxonomic_opinions` SYNONYM_OF로 마이그레이션하는 계획. |
| 096 | synonym_migration | 1,055건 동의어를 synonyms 테이블에서 taxonomic_opinions SYNONYM_OF로 마이그레이션. synonyms 테이블은 하위 호환 VIEW로 대체. 테스트 108개 통과. |
| 097 | synonym_manifest_and_fide_fix | genus_detail Synonymy 섹션 빈 항목 표시 수정; fide 매칭 개선으로 133건 추가 연결. 버전 0.2.4 발행. |

### 2026-02-28

| 번호/코드 | 제목 | 요약 |
|-----------|------|------|
| P71 | fix_country_id_and_formation_plan | country_id 오류 및 Formation 분류 불일치 수정 계획. |
| P72 | rebuild_pipeline_plan | `scripts/pipeline/` 모듈화 재빌드 파이프라인 설계 (8개 모듈). |
| P73 | rebuild_diff_resolution_plan | 재빌드 파이프라인과 기존 DB 간 diff 해소 계획. |
| P74 | assertion_centric_plan | Assertion-Centric 모델 설계: taxon/assertion/reference/classification_profile/classification_edge_cache 테이블 구조. |
| P74b | assertion_ui_parity_plan | Assertion DB UI 쿼리 40개 + manifest 15개 뷰 설계. |
| P75 | radial_tree_visualization_plan | 방사형(Radial) 트리 시각화 구현 계획. |
| 098 | fix_country_id_and_formation | 3,769건 country_id 오류 수정; Formation 불일치 350건(Type 1/2/3) 수정; 지역 93건 추가. 테스트 112개 통과. |
| 099 | rebuild_pipeline_complete | `scripts/pipeline/` 8개 모듈 파이프라인 구현 완료. 35/35 검증 통과. |
| 100 | rebuild_diff_resolution | 계층 파싱, SPELLING_OF 매핑, 동의어 추출, Formation 분류, bracket 제거 수정으로 SYNONYM_OF diff 0건 달성. |
| 101 | P74b_assertion_ui_parity | Assertion-Centric DB 생성(6,142 assertions, 5,083 edges); UI 쿼리 40개 + manifest 15개 뷰 추가. |
| 102 | treatise_taxonomy_extraction | Treatise 2004 Chapter 4(Agnostida)와 Chapter 5(Redlichiida) PDF에서 taxonomy JSON 추출. |

### 2026-03-01

| 번호/코드 | 제목 | 요약 |
|-----------|------|------|
| P76 | radial_tree_canonical_scoda | 기존 canonical DB의 parent_id를 직접 사용하는 Radial Tree 추가 계획. |
| P77 | versioned_db_filename | DB 파일명을 `{name}-{version}.db` 패턴으로 통일하는 계획. |
| P78 | treatise_import_plan | Treatise 2004 taxonomy를 assertion DB에 treatise2004 profile로 import하는 계획. |
| P79 | profile_selector_plan | UI에서 classification profile을 선택하는 `global_controls` manifest 기능 계획. |
| 102b | P75_radial_tree_assertion_impl | assertion DB와 canonical DB 모두에 Radial Tree 시각화 구현. scoda-engine radial.js에 subtree view, context menu, 접기/펼치기 추가. |
| 103 | P76_radial_tree_canonical_scoda | canonical trilobase.scoda에 parent_id 기반 radial tree 추가. |
| 104 | P77_versioned_db_filename | 모든 DB 파일을 `{name}-{version}.db`로 리네임. `scripts/db_path.py` 헬퍼 신설(find_trilobase_db 등). 테스트 112개 통과. |
| 105 | P78_treatise_import | Treatise 2004 Agnostida/Redlichiida를 assertion DB에 treatise2004 profile로 import (421 assertions, 5,138 edges). 테스트 112개 통과. |
| 106 | P79_profile_selector_ui | `global_controls` manifest 기능으로 UI profile selector 구현. taxonomy_tree/family_genera/taxon_children 쿼리를 profile-aware하게 수정. 테스트 112개 통과. |
| 107 | P80_assertion_crud | assertion DB manifest에 taxon/assertion/reference/profile CRUD `editable_entities` 추가. 테스트 118개 통과. |

### 2026-03-02

| 번호/코드 | 제목 | 요약 |
|-----------|------|------|
| R01 | taxonomy_management | 진화하는 taxonomy 관리를 위한 6가지 설계 아이디어 리뷰: Layered Profile, Assertion Timeline, Revision Package, Working Classification, Scope-Aware Assertion, Temporal Authority. |
| R02 | tree_diff_visualization | 프로필 비교 표시 4가지 모드(Diff Table, Diff Tree, Side-by-Side, Overlay)와 Animated Morphing 상세 구현 계획 리뷰. |

### 2026-03-06

| 번호/코드 | 제목 | 요약 |
|-----------|------|------|
| 108 | assertion_db_cleanup | classification profile 정리(ja2002_strict 삭제, default 이름 통일); placeholder taxon rank를 대문자로 수정. DB v0.1.4 발행. 테스트 118개 통과. |

### 2026-03-07

| 번호/코드 | 제목 | 요약 |
|-----------|------|------|
| P81 | side_by_side_tree_refactoring | tree_chart.js를 전역 상태에서 TreeChartInstance 클래스로 리팩토링 후 Side-by-Side 뷰 구현 계획. |
| 109 | treatise1959_import | Treatise 1959(Moore) 분류 체계를 수동 입력 + OCR로 추출 후 treatise1959 profile로 import (1,366 assertions, 5,323 edges). |
| 110 | assertion_v015_profile_fixes | treatise1959를 독립 standalone profile로 변경(1,324 edges); treatise2004는 treatise1959 기반으로 수정. 속 중복 및 placeholder 명명 수정. |
| 111 | profile_diff_table | Compare 모드 Phase 0+1 구현: compareMode 토글, compare_control manifest 기능, profile_diff SQL 쿼리, 행 색상 코딩 포함 profile_diff_table 뷰. |
| 112 | side_by_side_tree | tree_chart.js를 TreeChartInstance 클래스로 리팩토링; Side-by-Side 뷰에 두 인스턴스 구현 + zoom/pan 동기화. |
| 113 | sbs_sync_and_perf | 동기화 기능 5가지(hover highlight, depth toggle, collapse/expand, view-as-root, tooltip) 추가. bitmap cache + SVG 라벨 숨기기로 성능 최적화. |
| 114 | diff_tree | Diff Tree 뷰 구현: profile_diff_edges SQL, 색상 코딩 단일 트리(same/moved/added/removed), drawDiffLegend, ghost edges. Eodiscida/Eodiscina 분리 수정. |

### 2026-03-09

| 번호/코드 | 제목 | 요약 |
|-----------|------|------|
| P82 | animated_morphing_plan | Profile Comparison compound view 설계: Table/Tree/Morph 서브뷰, 모핑 애니메이션 transport 컨트롤. |
| 115 | compound_view_and_morphing | Compound view 구현 (Profile Comparison 탭 내 Table/Tree/Animation 서브뷰). 모핑 애니메이션 구현; genera_count 동적 계산(10,310ms → 9ms). DB v0.1.6 발행. |

### 2026-03-10

| 번호/코드 | 제목 | 요약 |
|-----------|------|------|
| 116 | treatise1959_txt_pipeline_and_fixes | `parse_treatise_txt.py` TXT→JSON 파이프라인 구현. EODISCINA_ID 하드코딩 버그 수정. Diff Tree rank_radius 수정. DB v0.1.7 발행. |

### 2026-03-11

| 번호/코드 | 제목 | 요약 |
|-----------|------|------|
| 117 | treatise1959_txt_cleanup | treatise_1959_taxonomy.txt에서 오타 25건 수정, 저자 accent 14명 복원, 형식 22건 수정. assertion DB 재빌드(8,331 assertions). |
| 118 | assertion_v018_ui_and_validation | 탭 라벨 간소화; 검증 스크립트를 profile별 Order 수 개별 체크로 개선. DB v0.1.8 발행. 17/17 검증 통과. R03 설계 문서 작성. |
| 119 | canonical_source_data | `convert_to_source_format.py` 작성; `data/sources/`에 5개 canonical source 파일 생성(R04 확장 형식: YAML 헤더 + 계층 본문). |
| 120 | assertion_db_020_source_build | `scripts/build_assertion_db.py` (~800줄) 단일 스크립트로 작성. `data/sources/*.txt` 기반 assertion DB 0.2.0 빌드(default 5,113 edges). |
| 121 | trilobase_030_rename_consolidation | trilobase-assertion → trilobase 이름 통합. `is_accepted` 컬럼 제거. 스크립트 7개 이름 통일, 60+개 레거시 스크립트 archive 이동. Trilobase 0.3.0 발행. 17/17 검증 통과. |
| 122 | handoff_claude_md_030_update | HANDOFF.md와 CLAUDE.md를 0.3.0 assertion-centric 스키마 기준으로 전면 갱신(-474줄). |
| 123 | genera_count_removal | `taxon` 테이블에서 `genera_count` 컬럼 제거; edge_cache 기반 동적 계산으로 전환. CI 실패 테스트 21건 수정. 테스트 117개 통과. |
| P83 | build_assertion_from_sources | `data/sources/*.txt`(R04 형식)를 단일 진입점으로 assertion DB를 빌드하는 6-Phase 파이프라인 설계. |
| P84 | tree_search_and_watch | Tree Chart 검색 버그 수정 + Watch 기능(노드 추적, 2× 크기 확대 렌더링, Watch 목록 패널) 계획. |
| R03 | comprehensive_scope_and_removal | "침묵의 의미는 출처의 범위(scope)에 의해 결정된다" 원칙 정립. `reference_scope` 테이블 설계 및 comprehensive removal 로직 제안. |
| R04 | taxonomy_input_format | R04 확장 TXT 형식 설계: YAML 헤더 + 계층 본문 마커(`?`, `-`, `=>`, `=`, `~`, `#`, `[incertae sedis]`). |
| R05 | assertion_018_vs_020_diff | 0.1.8 (3단계 파이프라인) vs 0.2.0 (소스 기반 단일 스크립트) 상세 차이 분석. Default profile 97.7% 일치, 나머지는 데이터 품질 개선. |

### 2026-03-12

| 번호/코드 | 제목 | 요약 |
|-----------|------|------|
| 001 | brachiobase_v020 | Treatise Brachiopoda Revised Vol 3(2000), 4(2002), 5(2006) PDF 전체 추출. 2-profile brachiobase DB(Profile 1: 1965, Profile 2: 2000-2006) 빌드. 총 taxa 5,826, assertions 6,987. |
| P85 | base_taxonomy_template | `scoda_engine_core.taxonomy_base` 모듈로 공통 쿼리 15개 + manifest 7개 뷰 추출 계획. TaxonomyConfig dataclass + merge 헬퍼 설계. |

### 2026-03-13

| 번호/코드 | 제목 | 요약 |
|-----------|------|------|
| 122 | brachiobase_ui_and_p85_plan | brachiobase에 Tree Chart + Profile Comparison compound 뷰 추가; `source_param` 버그 수정, rank_radius 수정. 테스트: trilobase 117, scoda-engine 250 통과. |
| P86 | multi_package_serving | URL prefix(`/api/{package}/...`) 기반 멀티 SCODA 패키지 동시 서빙 설계. PackageRegistry + FastAPI 라우팅 + Package Selector UI 계획. |

### 2026-03-14

| 번호/코드 | 제목 | 요약 |
|-----------|------|------|
| P87 | timeline_scoda_package_setup | trilobase 패키지에 `tree_chart_timeline` 서브뷰 활성화 작업 명세. geologic/pubyear 축 쿼리 6개 + manifest 수정 계획. |
| 123 | p87_timeline_implementation | Timeline 기능을 trilobase 패키지에 구현. ui_queries 46 → 52개. compound view `timeline` 탭 추가. Trilobase 0.3.1 발행. |
| 124 | p88_timeline_mya_slider | Timeline Geologic 슬라이더를 시대 코드 누적 방식에서 Mya 기반 스냅샷 방식으로 전환. `temporal_code_mya` 테이블 신설(31건). Research 축을 genus 명명 연도 기반으로 수정. |
| 125a | graptobase_v010 | Graptobase v0.1.0 빌드: Treatise Graptolithina 3판(1955/1970/2023) 기반. 3개 profile, genus 539건, assertions 1,022건. Timeline 기능 포함. scoda-engine 무한 루프 버그 수정. |
| 125b | brachiobase_timeline | Brachiobase v0.2.2: temporal code 추출(4,664 속 중 3,960건 84.9%) + Timeline(geologic LCAM~Recent + pubyear) 기능 추가. |

### 2026-03-15

| 번호/코드 | 제목 | 요약 |
|-----------|------|------|
| 126 | tsf_expansion_new_source_files | TSF 소스 파일 대규모 확장: ammonoidea_1957 완성(2,632줄) + 신규 5종 추가(ammonoidea_1996, bryozoa_1953, cephalopoda_1964, coelenterata_1956, mollusca_1960, archaeocyatha_porifera_1955). pdf-to-taxonomy 스킬 배치 처리 지원 추가. TSF 명세 문서(v0.1) 작성. 총 소스 파일 23개. |
| 127 | brachiobase_v023_hierarchy_fix | Brachiobase Profile 2의 Order들이 Phylum에 직접 연결되는 계층 버그 수정. `brachiopoda_classification.txt` 사전 레퍼런스 파일로 167개 structural edge 생성. Profile 2 bridge edges: 25개 → 0개. v0.2.3 발행. |

---

## 주제별 그룹

### A. 인프라 / 아키텍처

| 파일 | 내용 |
|------|------|
| P62, 078 | scoda-engine 레포 분리 |
| 079 | db/dist 디렉토리 재편 |
| P63 | 미래 로드맵 |
| P67 | SCODA 명세 동기화 |
| P68, 090 | GitHub Actions CI/CD |
| 094, 095 | Hub manifest 생성 |
| P69 | MkDocs 문서 사이트 계획 |
| P77, 104 | DB 파일명 버전화 |
| 122 (0311) | HANDOFF.md / CLAUDE.md 갱신 |
| P85 | taxonomy_base 공통 모듈 계획 |
| P86 | Multi-package 서빙 계획 |

### B. 데이터 품질

| 파일 | 내용 |
|------|------|
| 080 | NULL parent 13개 속 수정 |
| 081 | 연결되지 않은 동의어 수정 |
| 082 | 대규모 인코딩/하이픈/공백 수정 |
| 084 | NULL parent Family → Order Uncertain |
| 086 | 철자 변이 중복 수정 |
| 087 | temporal code 84건 보완 |
| 088 | NULL parent_id 전량 해소 |
| 093 | country_id 오류 수정 |
| 098 | country_id 3,769건 + Formation 350건 수정 |
| 117 | Treatise 1959 txt 25건 오타 수정 |

### C. DB 스키마 / 모델 진화

| 파일 | 내용 |
|------|------|
| P64, 083 | taxon_bibliography junction table |
| P65, 085 | 버전 관리 프로세스 |
| 086-088 | SPELLING_OF opinion 타입, Agnostida Order |
| P70, 096 | synonyms → SYNONYM_OF 마이그레이션 |
| P72, 099 | scripts/pipeline/ 모듈화 재빌드 |
| P74, 101 | Assertion-Centric 모델 (핵심 전환) |
| 119 | canonical source files (R04 형식) |
| 120 | build_assertion_db.py 단일 빌드 스크립트 |
| 121 | trilobase 0.3.0 통합 (is_accepted 제거) |
| 123 (0311) | genera_count 컬럼 제거 → 동적 계산 |
| R03, R04 | Scope/Removal 모델, TSF 입력 형식 설계 |

### D. UI / 시각화

| 파일 | 내용 |
|------|------|
| 089 | label_map 동적 컬럼 |
| 091 | genus_detail linked_table |
| 092 | rank_detail 리다이렉트 |
| 106 | profile selector UI |
| 107 | editable_entities CRUD |
| 111 | Profile Diff Table |
| P81, 112 | Side-by-Side Tree (TreeChartInstance) |
| 113 | 동기화 5기능 + 성능 최적화 |
| 114 | Diff Tree (색상 코딩 단일 트리) |
| P82, 115 | Compound view + 모핑 애니메이션 |
| P87, 123 (0314) | Timeline 기능 구현 |
| 124 | Timeline Mya 기반 슬라이더 |

### E. Radial Tree 시각화

| 파일 | 내용 |
|------|------|
| P75, 102b | assertion DB + canonical DB radial tree |
| P76, 103 | canonical scoda radial tree |
| 116 | TXT→JSON 파이프라인, diff tree 수정 |
| 118 | 탭 라벨 간소화, per-profile 검증 |

### F. Treatise 임포트

| 파일 | 내용 |
|------|------|
| 102 | Treatise 2004 Ch4/Ch5 PDF → JSON |
| P78, 105 | Treatise 2004 → treatise2004 profile |
| 109 | Treatise 1959 임포트 (treatise1959 profile) |
| 110 | 프로필 독립화 수정 |
| 116 | Treatise 1959 TXT→JSON 파이프라인 |
| 117 | Treatise 1959 데이터 정제 |

### G. Multi-DB / 패키지 확장

| 파일 | 내용 |
|------|------|
| 001 (0312) | Brachiobase v0.2.0 (Brachiopoda 2-profile) |
| 122 (0313) | Brachiobase UI 개선 |
| 125a | Graptobase v0.1.0 (Graptolithina 3-profile) |
| 125b | Brachiobase v0.2.2 (Timeline 추가) |
| 127 | Brachiobase v0.2.3 (계층 버그 수정) |
| 126 | TSF 소스 파일 23개 확장, TSF 명세 문서 |

### H. 리뷰 / 설계 문서

| 파일 | 내용 |
|------|------|
| R01 | Taxonomy 관리 6가지 설계 아이디어 |
| R02 | Tree Diff 시각화 4가지 모드 설계 |
| R03 | Comprehensive Scope & Removal 원칙 |
| R04 | TSF 입력 형식 상세 설계 |
| R05 | 0.1.8 vs 0.2.0 차이 분석 |

---

## 테스트 수 이력

| 날짜 | 파일 | 테스트 수 | 비고 |
|------|------|----------|------|
| 2026-02-19 | 078 | 66 | scoda-engine 분리 직후 |
| 2026-02-20 | 083 | 82 | taxon_bibliography 추가 |
| 2026-02-22 | 086 | 92 | Agnostida Order |
| 2026-02-22 | 087 | 100 | SPELLING_OF |
| 2026-02-22 | 088 | 100 | NULL parent_id 해소 |
| 2026-02-23 | 089 | 101 | label_map |
| 2026-02-24 | 092 | 101 | rank_detail 수정 |
| 2026-02-24 | 093 | 101 | query 수정 |
| 2026-02-27 | 096 | 108 | synonym 마이그레이션 |
| 2026-02-28 | 098 | 112 | country_id/formation |
| 2026-03-01 | 104 | 112 | versioned DB |
| 2026-03-01 | 105 | 112 | treatise2004 import |
| 2026-03-01 | 106 | 112 | profile selector |
| 2026-03-01 | 107 | 118 | CRUD editable_entities |
| 2026-03-06 | 108 | 118 | assertion DB cleanup |
| 2026-03-11 | 123 | 117 | genera_count 컬럼 제거 (-1) |
| 2026-03-13 | 122 | 117 | brachiobase UI, trilobase 유지 |
| 2026-03-14 | 123-124 | 117 | Timeline, Mya 슬라이더 |
| 2026-03-15 | 127 | 117 | brachiobase v0.2.3 |

---

## 버전 이력

### Trilobase (메인 DB)

| 버전 | 날짜 | 파일 | 주요 변경 |
|------|------|------|-----------|
| 0.2.0 | 2026-02-21 | 085 | 버전 관리 체계 도입 |
| 0.2.4 | 2026-02-27 | 097 | fide 매칭 개선, synonym 표시 수정 |
| 0.3.0 | 2026-03-11 | 121 | trilobase-assertion 통합, is_accepted 제거, 소스 기반 빌드 |
| 0.3.1 | 2026-03-14 | 123 | Timeline 기능 추가 |

### Trilobase Assertion DB (중간 단계, 0.3.0 통합 전)

| 버전 | 날짜 | 파일 | 주요 변경 |
|------|------|------|-----------|
| v0.1.4 | 2026-03-06 | 108 | profile 정리, rank 대문자화 |
| v0.1.5 | 2026-03-07 | 110 | treatise 프로필 독립화 |
| v0.1.6 | 2026-03-09 | 115 | compound view, 모핑 애니메이션 |
| v0.1.7 | 2026-03-10 | 116 | TXT pipeline, diff tree 수정 |
| v0.1.7 (재빌드) | 2026-03-11 | 117 | Treatise 1959 데이터 정제 |
| v0.1.8 | 2026-03-11 | 118 | 탭 라벨, per-profile 검증 |
| v0.2.0 | 2026-03-11 | 120 | 소스 기반 단일 스크립트 빌드 |

### Brachiobase

| 버전 | 날짜 | 파일 | 주요 변경 |
|------|------|------|-----------|
| v0.2.0 | 2026-03-12 | 001 | Revised Vol3/4/5 추가, 2-profile |
| v0.2.0 (재빌드) | 2026-03-13 | 122 | Tree Chart + Profile Comparison UI |
| v0.2.2 | 2026-03-14 | 125b | temporal code + Timeline 기능 |
| v0.2.3 | 2026-03-15 | 127 | 계층 구조 버그 수정 |

### Graptobase

| 버전 | 날짜 | 파일 | 주요 변경 |
|------|------|------|-----------|
| v0.1.0 | 2026-03-14 | 125a | 최초 릴리스. 3개 profile(1955/1970/2023) |

### PaleoCore

| 버전 | 날짜 | 파일 | 주요 변경 |
|------|------|------|-----------|
| 0.1.1 | 2026-02-21 | 085 | 버전 관리 체계 도입 |

---

## 통계

### 전체 기간 작업 건수

| 유형 | 건수 |
|------|------|
| 작업 로그 (숫자 번호) | 51 |
| 계획 문서 (P##) | 26 |
| 리뷰 문서 (R##) | 5 |
| 기타 | 5 |
| **합계** | **87** |

### 최종 DB 통계 (2026-03-15 기준)

| DB | 버전 | Genera | Assertions | Profiles |
|----|------|--------|------------|----------|
| Trilobase | 0.3.1 | ~5,156 | 8,382+ | 3 |
| Brachiobase | 0.2.3 | 4,664 | 6,987+ | 2 |
| Graptobase | 0.1.0 | 539 | 1,022 | 3 |
| PaleoCore | 0.1.1 | — | — | — |

### data/sources/ 파일 현황 (2026-03-15 기준)

총 **23개** TSF 소스 파일:

- 삼엽충 (Trilobita): 5개 (jell_adrain_2002, adrain_2011, treatise_1959, treatise_2004_ch4/ch5)
- 완족류 (Brachiopoda): 7개 (1965 vol1/vol2, 2000 vol2/vol3, 2002 vol4, 2006 vol5, brachiopoda_classification)
- 필석류 (Graptolithina): 3개 (1955, 1970, 2023)
- 암모나이트 (Ammonoidea): 2개 (1957, 1996)
- 그 외: bryozoa_1953, cephalopoda_1964, coelenterata_1956, mollusca_1960, archaeocyatha_porifera_1955, chelicerata_1955, ostracoda_1961
