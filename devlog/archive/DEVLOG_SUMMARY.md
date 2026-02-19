# Trilobase 개발 기록 요약

**최종 업데이트:** 2026-02-17
**총 문서:** 139개 (작업 로그 79개, 계획 문서 57개, 리뷰 2개, 기타 1개)
**개발 기간:** 2026-02-04 ~ 2026-02-17 (14일)

---

## 날짜별 작업 요약

### 2026-02-04 (Day 1) — 데이터 정제 및 DB 구축

Phase 1~7을 하루 만에 완료. 원본 PDF에서 추출한 텍스트를 정제하여 데이터베이스화하는 기초 작업.

| # | Phase | 제목 | 문서 |
|---|-------|------|------|
| 001 | 1 | 줄 정리 (Line Normalization) | `001_phase1_line_normalization.md` |
| 002 | 2 | 깨진 문자 및 오타 수정 (424건) | `002_phase2_character_fixes.md` |
| 003 | 3 | 데이터 검증 (Data Validation) | `003_phase3_data_validation_summary.md` |
| 004 | 4 | DB 스키마 설계 및 데이터 임포트 | `004_phase4_database_creation.md` |
| 005 | 5 | 데이터베이스 정규화 (Synonym, Formation, Location) | `005_phase5_normalization.md` |
| 006 | 6 | Family 정규화 (181개) | `006_phase6_family_normalization.md` |
| 007 | 7 | Order 통합 및 계층 구조 구축 | `007_phase7_order_integration.md` |

**계획 문서:** P01 — 데이터 정제 및 데이터베이스 구축 계획

---

### 2026-02-05 (Day 2) — DB 통합 + 웹 인터페이스 + Bibliography

DB 스키마 통합(Phase 8-9), 관계 테이블(Phase 10), 웹 UI(Phase 11), 참고문헌(Phase 12)까지 완료.

| # | Phase | 제목 | 문서 |
|---|-------|------|------|
| 008 | 8 | Taxonomy Table Consolidation (taxonomic_ranks 통합) | `008_phase8_taxonomy_consolidation_complete.md` |
| 009 | 9 | Taxa와 Taxonomic_ranks 통합 | `009_phase9_taxa_consolidation_complete.md` |
| 010 | 10 | Formation/Location Relation 테이블 (다대다) | `010_phase10_formation_location_relations_complete.md` |
| 011 | 11 | Web Interface (Flask, Tree View, Detail Modal) | `011_phase11_web_interface_complete.md` |
| 012 | — | 데이터 정리 및 UI 개선 (Phase 11 후속) | `012_data_cleanup_and_ui_improvements.md` |
| 013 | — | UI 필터 및 네비게이션 개선 | `013_ui_filter_and_navigation.md` |
| 014 | 12 | Bibliography 테이블 구축 (2,130건) | `014_phase12_bibliography_complete.md` |
| 015 | — | 향후 작업 제안사항 | `015_future_work_proposals.md` |

**계획 문서:** P02 (Phase 8), P03 (Phase 9), P04 (Phase 10), P05 (Phase 11), P06 (Phase 12)

---

### 2026-02-06 (Day 3) — UI 버그픽스 + 테스트

| # | 제목 | 문서 |
|---|------|------|
| 001 | UI 개선: Statistics 중복 제거 및 Children 네비게이션 | `20260206_001_ui_fixes.md` |
| 002 | app.py 테스트 작성 | `20260206_002_app_tests.md` |

---

### 2026-02-07 (Day 4) — SCODA 구현 + 독립 실행형 앱

SCODA(Self-Contained Data Artifact) 메타데이터부터 PyInstaller 패키징까지 Phase 13~19를 하루 만에 완료. 프로젝트의 큰 전환점.

| # | Phase | 제목 | 문서 |
|---|-------|------|------|
| 012 | 13 | SCODA-Core 메타데이터 (Identity, Provenance, Semantics) | `012_phase13_scoda_core_complete.md` |
| 013 | 14 | Display Intent + Saved Queries | `013_phase14_display_intent_queries_complete.md` |
| 014 | 15 | UI Manifest (선언적 뷰 정의) | `014_phase15_ui_manifest.md` |
| 015 | 16 | 릴리스 메커니즘 (SHA-256, 불변성) | `015_phase16_release_mechanism.md` |
| 016 | 17 | Local Overlay (사용자 주석) | `016_phase17_local_overlay.md` |
| 017 | 18 | 독립 실행형 앱 (PyInstaller, 13-15MB) | `017_standalone_executable_complete.md` |
| 018 | 19 | GUI 컨트롤 패널 (tkinter) | `018_gui_control_panel_complete.md` |

**계획 문서:** P07 (SCODA 전체 계획), P08 (릴리스), P09 (Overlay), P10 (PyInstaller), P11 (GUI), P12 (Overlay DB 분리)
**리뷰 문서:** R01 (Local Overlay 내구성), R02 (배포 형식)

---

### 2026-02-08 (Day 5) — Overlay DB 분리 + GUI 로그 뷰어

PyInstaller read-only 문제 해결과 디버깅 지원.

| # | Phase | 제목 | 문서 |
|---|-------|------|------|
| 020 | 20 | Overlay DB 분리 (Canonical read-only + Overlay read/write) | `020_overlay_db_separation.md` |
| 021 | 21 | GUI 로그 뷰어 (실시간 Flask 로그, 색상별 레벨) | `021_gui_log_viewer_complete.md` |

**계획 문서:** P13 (GUI 로그 뷰어)

---

### 2026-02-09 (Day 6) — MCP Server

LLM이 자연어로 Trilobase를 쿼리할 수 있는 MCP(Model Context Protocol) 서버 구현.

| # | Phase | 제목 | 문서 |
|---|-------|------|------|
| 022 | — | Sticky Table Header 버그 수정 | `022_fix_sticky_table_header.md` |
| 022 | 22 | MCP Server (14개 도구, stdio 모드) | `022_phase22_mcp_server.md` |

**계획 문서:** P14 (MCP Server 계획), SCODA_MCP_Wrapping_Plan

---

### 2026-02-10 (Day 7) — MCP SSE 통합 + EXE 분리 + 데이터 수정

MCP 서버의 배포 형태를 반복적으로 개선. SSE 통합 → 독립 실행 → GUI에서 분리 → EXE 2개 분리.

| # | Phase | 제목 | 문서 |
|---|-------|------|------|
| 023 | 23 | MCP Server SSE 통합 (Starlette + Uvicorn, 포트 8081) | `023_phase23_mcp_sse_integration.md` |
| 024 | 24 | GUI MCP SSE 독립 실행 분리 (선택적 옵션) | `024_phase24_gui_mcp_sse_optional.md` |
| 025 | — | Single EXE with MCP stdio Mode | `025_phase25_mcp_stdio_single_exe.md` |
| 026 | — | GUI MCP SSE UI 요소 제거 | `026_gui_remove_mcp_sse_ui.md` |
| 028 | — | EXE 2개 분리 (trilobase.exe + trilobase_mcp.exe) | `028_two_exe_split.md` |
| 029 | — | DB 파싱 오류 16건 수정 + 누락 genus 2건 추가 | `029_parsing_error_fixes.md` |
| 030 | — | MCP 테스트 asyncio 호환성 수정 | `030_mcp_test_asyncio_fix.md` |

**계획 문서:** P15 (SSE 통합), P16 (stdio EXE), P17 (SSE 선택적), P18 (SSE UI 제거), P19 (EXE 분리)

---

### 2026-02-12 (Day 8) — 외부 데이터 도입 + 지리/시간 체계

.scoda 패키지 포맷 도입 후, COW 국가 데이터, Geographic Regions, ICS 지질시대 데이터를 연속 임포트. 하루에 Phase 25~30 (6개 Phase) 완료.

| # | Phase | 제목 | 문서 |
|---|-------|------|------|
| 030 | 25 | .scoda ZIP 패키지 포맷 도입 및 DB-앱 분리 | `030_phase25_scoda_package.md` |
| 031 | — | Countries 데이터 품질 정리 (151→142개) | `031_countries_data_quality.md` |
| 032 | 26 | COW State System v2024 도입 (244 레코드, 매핑률 96.5%) | `032_phase26_cow_import.md` |
| 033 | — | Web UI 상세 페이지 및 상호 링크 | `033_web_detail_pages.md` |
| 034 | — | Genus Detail Geographic 중복 제거 | `034_genus_detail_geo_dedup.md` |
| 035 | 27 | Geographic Regions 계층 구조 (562건, 100% 매핑) | `035_phase27_geographic_regions.md` |
| 036 | 28 | ICS Chronostratigraphic Chart 임포트 (178 concept) | `036_phase28_ics_import.md` |
| 037 | 29 | ICS Chronostratigraphy 웹 UI | `037_phase29_ics_web_ui.md` |
| 038 | 30 | ICS Chart 뷰 (계층형 색상 코딩 테이블) | `038_phase30_ics_chart_view.md` |

**계획 문서:** P20 (.scoda 포맷), P21 (COW 도입), P22 (상세 페이지), P23 (Regions), P24 (ICS 임포트), P25 (ICS UI), P26 (ICS Chart)

---

### 2026-02-13 (Day 9) — PaleoCore 분리 + Manifest UI + 범용 뷰어

프로젝트 역사상 가장 많은 작업량. PaleoCore DB 분리(Phase 31-37), 리브랜딩(Phase 38), 선언적 UI(Phase 39-41), 범용 뷰어(Phase 42-43)까지 15개 작업 로그.

**주제 1: PaleoCore DB 분리 (Phase 31-37)**

| # | Phase | 제목 | 문서 |
|---|-------|------|------|
| 039 | 31 | PaleoCore DB 생성 스크립트 (14개 테이블, 3,340 레코드) | `039_paleocore_db_creation.md` |
| 040 | 32 | Dual-DB 운영 (PaleoCore ATTACH, 3-DB 동시) | `040_phase32_dual_db.md` |
| 041 | 33 | PaleoCore 쿼리 `pc.*` prefix 전환 | `041_phase33_pc_prefix.md` |
| 042 | 34 | trilobase.db에서 PaleoCore 테이블 DROP (8개) | `042_phase34_drop_paleocore_tables.md` |
| 043 | 35 | PaleoCore .scoda 패키지 + Dependency 반영 | `043_phase35_paleocore_scoda.md` |
| 044 | 36 | 조합 .scoda 배포 테스트 | `044_phase36_combined_scoda_test.md` |
| 045 | 37 | PyInstaller 빌드에 paleocore.scoda 포함 | `045_phase37_build_paleocore_scoda.md` |

**주제 2: 리브랜딩 + 버그픽스**

| # | Phase | 제목 | 문서 |
|---|-------|------|------|
| 046 | 38 | GUI를 "SCODA Desktop"으로 리브랜딩 | `046_phase38_scoda_desktop_rebranding.md` |
| 047 | — | Bugfix: taxa_count 컬럼 참조 제거 (API 500 에러) | `047_fix_taxa_count_column.md` |
| 048 | — | Bugfix: ui_queries의 taxa_count 컬럼 참조 오류 | `048_fix_named_query_taxa_count.md` |

**주제 3: 선언적 UI + 범용 뷰어 (Phase 39-43)**

| # | Phase | 제목 | 문서 |
|---|-------|------|------|
| 049 | 39 | Declarative Manifest Schema + UI Migration (-188줄) | `049_phase39_declarative_manifest_ui.md` |
| 050 | 40 | CORS + Custom SPA Example + EXE Renaming | `050_phase40_cors_spa_rename.md` |
| 051 | 41 | Manifest-Driven Tree & Chart Rendering | `051_phase41_manifest_tree_chart.md` |
| 052 | 42 | Generic SCODA Package Viewer (Namespaced API) | `052_phase42_generic_scoda_viewer.md` |
| 052 | 43 | Docker Desktop 스타일 컨트롤 패널 + 단일 패키지 서빙 | `052_phase43_control_panel_single_package.md` |

**계획 문서:** P27 (PaleoCore 스키마), P28-P31 (Phase 34-37), P32 (리브랜딩), P33-P37 (Phase 39-43)

---

### 2026-02-14 (Day 10) — Reference SPA + Runtime Purification

Trilobase 전용 코드를 분리하여 SCODA Desktop을 완전한 범용 뷰어로 만드는 대작업. ~1,200줄 legacy 코드 제거.

| # | Phase | 제목 | 문서 |
|---|-------|------|------|
| 053 | 44 | Reference Implementation SPA (generic viewer + standalone SPA 분리) | `053_phase44_reference_spa.md` |
| 054 | 45 | 디렉토리 구조 정리 — Runtime/Data 분리 | `054_phase45_directory_restructure.md` |
| 055 | 46-1 | Generic Composite Detail Endpoint (21개 named query 추가) | `055_phase46_step1_composite_endpoint.md` |
| 056 | 46-2 | Dynamic MCP Tool Loading from .scoda Packages | `056_phase46_step2_dynamic_mcp_tools.md` |
| 057 | 46-3 | Legacy Code Removal (~1,200줄, 도메인 코드 0줄) | `057_phase46_step3_legacy_removal.md` |
| 058 | — | Reference SPA API 연동 수정 | `058_spa_api_fixes.md` |
| 059 | — | SPA 브랜딩 변경 (Trilobase) + 글로벌 검색 (Ctrl+K) | `059_spa_branding_global_search.md` |

**계획 문서:** P38 (Reference SPA), P39 (디렉토리 정리), P40 (Runtime Purification), P41 (SPA 브랜딩)

---

### 2026-02-15 (Day 11) — UID + FastAPI + MCP 통합

UID 100% 커버리지 달성. Flask→FastAPI 전환 완료. MCP SSE를 FastAPI sub-app으로 통합하여 단일 프로세스화.

| # | 제목 | 문서 |
|---|------|------|
| 060 | UID Population Phase A — 확정적 UID 6,250건 생성 | `060_uid_population_phase_a.md` |
| 061 | UID Population Phase B — 품질 수정 + same_as_uid 연결 | `061_uid_population_phase_b.md` |
| 062 | UID Population Phase C — Bibliography + Formations fp_v1 (10,384건 100%) | `062_uid_population_phase_c.md` |
| 063 | Flask → FastAPI 마이그레이션 (단일 ASGI 스택) | `063_fastapi_migration.md` |
| 064 | Formation country/period 데이터 채우기 (99.65%/98.6%) | `064_formation_metadata_backfill.md` |
| 065 | Formation Detail 링크 추가 (Country, Period→ICS) | `065_formation_detail_links.md` |
| 066 | MCP + Web API 단일 프로세스 통합 (/mcp sub-app) | `066_mcp_web_api_merge.md` |
| 067 | Pydantic response_model 추가 (OpenAPI 자동 문서화) | `067_pydantic_response_model.md` |

**계획 문서:** P42-P44 (UID Phase A-C), P45 (향후 로드맵), P46 (FastAPI), P47 (Formation backfill), P48 (MCP 통합), P49 (Pydantic)

---

### 2026-02-16 (Day 12) — Generic Viewer 리팩토링 + 버그 수정

Hierarchy View 통합, Taxonomic Opinions 설계 문서 완성, 버그 수정 2건.

| # | 제목 | 문서 |
|---|------|------|
| 068 | Nav History Back Button (미동작, 롤백 예정) | `068_nav_history_back_button.md` |
| 069 | Generic Viewer 도메인 독립화 + Entity Detail API | `069_generic_viewer_refactor.md` |
| 070 | Hierarchy View 일반화 — tree + nested_table → `type: "hierarchy"` 통합 | `070_hierarchy_view_unification.md` |
| 071 | Bugfix: PaleoCore chronostratigraphy chart 정렬 오류 (chart_options 누락) | `071_fix_paleocore_chart_options.md` |
| 072 | Bugfix: Bibliography detail이 전체 genera 표시 (composite 미전환) | `072_fix_bibliography_genera.md` |

**계획 문서:** P50-P52 (Taxonomic Opinions 설계/리뷰/최종), P53 (Assertion-Centric 모델), P54 (Auto-Discovery), P55 (Hierarchy 통합)

---

### 2026-02-17 (Day 13) — 로드맵 정리

| 제목 | 문서 |
|------|------|
| 2026 Q1 로드맵 (Track A/B/C) | `P56_roadmap_2026Q1.md` |

**계획 문서:** P56 (2026 Q1 로드맵)

---

## 주제별 분류

### 1. 데이터 정제 및 DB 구축 (Phase 1-12)

원본 PDF → 텍스트 추출 → 정제 → DB 임포트 → 정규화 → 웹 UI → 참고문헌

| 날짜 | Phase | 내용 |
|------|-------|------|
| 02-04 | 1-7 | 줄 정리, 문자 수정, 검증, DB 생성, 정규화, Family, Order |
| 02-05 | 8-12 | 테이블 통합, 관계 테이블, 웹 UI, Bibliography |

### 2. SCODA 프레임워크 (Phase 13-17, 25, 35-46)

Self-Contained Data Artifact 개념을 설계하고 구현. 메타데이터 → 릴리스 → 패키지 포맷 → 범용 뷰어로 진화.

| 날짜 | Phase | 내용 |
|------|-------|------|
| 02-07 | 13-17 | SCODA-Core 메타데이터, Display Intent, Manifest, 릴리스, Overlay |
| 02-12 | 25 | .scoda ZIP 패키지 포맷 |
| 02-13 | 35-38 | PaleoCore .scoda, 조합 배포 테스트, SCODA Desktop 리브랜딩 |
| 02-13 | 39-43 | Declarative Manifest UI, 범용 뷰어, Docker Desktop 스타일 GUI |
| 02-14 | 44-46 | Reference SPA 분리, Runtime Purification, Legacy 제거 |

### 3. 독립 실행형 앱 (Phase 18-21)

PyInstaller 패키징, GUI, Overlay DB 분리, 로그 뷰어.

| 날짜 | Phase | 내용 |
|------|-------|------|
| 02-07 | 18-19 | PyInstaller EXE, tkinter GUI |
| 02-08 | 20-21 | Overlay DB 분리, GUI 로그 뷰어 |

### 4. MCP Server (Phase 22-24)

LLM을 위한 Model Context Protocol 서버. stdio → SSE → EXE 분리 → FastAPI 통합.

| 날짜 | Phase | 내용 |
|------|-------|------|
| 02-09 | 22 | MCP Server 구현 (14개 도구, stdio) |
| 02-10 | 23-24 | SSE 통합, GUI 통합/분리, EXE 2개 분리 |
| 02-14 | 46-2 | Dynamic MCP Tool Loading (.scoda 패키지 기반) |
| 02-15 | — | MCP + Web API 단일 프로세스 통합 (/mcp sub-app mount) |

### 5. 외부 데이터 도입 (Phase 26-30)

국제 표준 데이터(COW, ICS)를 임포트하여 Trilobase 데이터와 연결.

| 날짜 | Phase | 내용 |
|------|-------|------|
| 02-12 | 26 | COW State System v2024 (국가 매핑 96.5%) |
| 02-12 | 27 | Geographic Regions 계층 구조 (562건) |
| 02-12 | 28-30 | ICS Chronostratigraphic Chart 임포트 + 웹 UI + Chart 뷰 |

### 6. PaleoCore 분리 (Phase 31-37)

범용 데이터(국가, 지층, 지질시대)를 별도 패키지로 분리.

| 날짜 | Phase | 내용 |
|------|-------|------|
| 02-13 | 31-34 | PaleoCore DB 생성, Dual-DB, pc.* prefix, DROP |
| 02-13 | 35-37 | PaleoCore .scoda, 조합 테스트, 빌드 포함 |

### 7. UID (Stable Unique Identifier)

전체 엔티티에 안정적인 고유 식별자 부여.

| 날짜 | 내용 |
|------|------|
| 02-15 | Phase A: 확정적 UID 6,250건 (ICS, temporal, countries, regions, taxonomy) |
| 02-15 | Phase B: 품질 수정, same_as_uid 연결 |
| 02-15 | Phase C: Bibliography + Formations fp_v1 (10,384건 100% 커버리지) |

### 8. 인프라 전환 (02-15)

| 날짜 | 내용 |
|------|------|
| 02-15 | Flask → FastAPI 마이그레이션 (단일 ASGI 스택) |
| 02-15 | MCP + Web API 단일 프로세스 통합 |
| 02-15 | Pydantic response_model (OpenAPI 자동 문서화) |

### 9. Generic Viewer 강화 (02-16)

| 날짜 | 내용 |
|------|------|
| 02-16 | Generic Viewer 도메인 독립화 + Entity Detail API |
| 02-16 | Hierarchy View 통합 (tree + nested_table → `type: "hierarchy"`) |

### 10. 버그 수정 및 데이터 품질

| 날짜 | 내용 | 문서 |
|------|------|------|
| 02-06 | UI Statistics 중복, Children 네비게이션 | `20260206_001_ui_fixes.md` |
| 02-09 | Sticky Table Header | `20260209_022_fix_sticky_table_header.md` |
| 02-10 | DB 파싱 오류 16건 + 누락 genus 2건 | `20260210_029_parsing_error_fixes.md` |
| 02-10 | MCP 테스트 asyncio 호환성 | `20260210_030_mcp_test_asyncio_fix.md` |
| 02-12 | Countries 데이터 품질 (151→142개) | `20260212_031_countries_data_quality.md` |
| 02-12 | Genus Detail Geographic 중복 제거 | `20260212_034_genus_detail_geo_dedup.md` |
| 02-13 | taxa_count 컬럼 참조 에러 (API + named query) | `047`, `048` |
| 02-14 | Reference SPA API 연동 수정 | `20260214_058_spa_api_fixes.md` |
| 02-15 | Formation country/period 데이터 채우기 | `064_formation_metadata_backfill.md` |
| 02-16 | PaleoCore chart_options 누락 (정렬 오류) | `071_fix_paleocore_chart_options.md` |
| 02-16 | Bibliography detail 전체 genera 표시 | `072_fix_bibliography_genera.md` |

### 11. 설계 문서 (미구현)

| 날짜 | 문서 | 주제 | 상태 |
|------|------|------|------|
| 02-16 | P50-P52 | Taxonomic Opinions (설계→리뷰→최종) | 설계 완료, 구현 대기 |
| 02-16 | P53 | Assertion-Centric Canonical Model (장기 비전) | 설계 완료, 조건부 |
| 02-16 | P54 | Generic Viewer Auto-Discovery | 설계 완료, 구현 대기 |
| 02-17 | P56 | 2026 Q1 로드맵 (Track A/B/C) | 현행 |

---

## 문서 유형 통계

| 유형 | 접두사 | 개수 | 설명 |
|------|--------|------|------|
| 작업 로그 | `NNN` (숫자) | 79 | 완료된 작업의 상세 기록 |
| 계획 문서 | `PNN` | 57 | 작업 전 설계/계획 |
| 리뷰 문서 | `RNN` | 2 | 아키텍처 검토 |
| 기타 | — | 1 | SCODA MCP Wrapping Plan (초기 문서) |

## Phase 진행표

| Phase | 날짜 | 주제 |
|-------|------|------|
| 1-7 | 02-04 | 데이터 정제, DB 구축, 정규화 |
| 8-10 | 02-05 | 테이블 통합, 관계 테이블 |
| 11-12 | 02-05 | 웹 인터페이스, Bibliography |
| 13-19 | 02-07 | SCODA 메타데이터, 릴리스, Overlay, PyInstaller, GUI |
| 20-21 | 02-08 | Overlay DB 분리, GUI 로그 뷰어 |
| 22 | 02-09 | MCP Server |
| 23-24 | 02-10 | MCP SSE 통합, GUI 분리 |
| 25 | 02-12 | .scoda ZIP 패키지 포맷 |
| 26-30 | 02-12 | COW, Regions, ICS 임포트/UI |
| 31-38 | 02-13 | PaleoCore 분리, 리브랜딩 |
| 39-43 | 02-13 | Declarative Manifest, 범용 뷰어, 컨트롤 패널 |
| 44-46 | 02-14 | Reference SPA, 디렉토리 정리, Runtime Purification |
| UID A-C | 02-15 | Stable UID Population (10,384건) |
| — | 02-15 | FastAPI 전환, MCP 통합, Pydantic |
| — | 02-16 | Hierarchy 통합, 버그 수정, Taxonomic Opinions 설계 |
| — | 02-17 | 2026 Q1 로드맵 정리 (P56) |
