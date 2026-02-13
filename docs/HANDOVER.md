# Trilobase 프로젝트 Handover

**마지막 업데이트:** 2026-02-13

## 프로젝트 개요

삼엽충(trilobite) 분류학 데이터베이스 구축 프로젝트. Jell & Adrain (2002) PDF에서 추출한 genus 목록을 정제하여 데이터베이스화하는 것이 목표.

## 현재 상태

### 완료된 작업

- **Phase 1 완료**: 줄 정리 (한 genus = 한 줄)
- **Phase 2 완료**: 깨진 문자 및 오타 수정 (총 424건)
- **Phase 3 완료**: 데이터 검증
- **Phase 4 완료**: DB 스키마 설계 및 데이터 임포트
- **Phase 5 완료**: 데이터베이스 정규화 (Synonym, Formation, Location)
- **Phase 6 완료**: Family 정규화 (181개)
- **Phase 7 완료**: Order 통합 및 계층 구조 구축
- **Phase 8 완료**: taxonomic_ranks와 families 테이블 통합
- **Phase 9 완료**: taxa와 taxonomic_ranks 테이블 통합
- **Phase 10 완료**: Formation/Location Relation 테이블
  - genus_formations 테이블 생성 (4,854건)
  - genus_locations 테이블 생성 (4,841건)
  - 다대다 관계 지원
  - 원본 텍스트 필드 보존

- **Phase 11 완료**: Web Interface
  - Flask 기반 웹 애플리케이션
  - Tree View (Class~Family 계층 구조)
  - Genus List (Family 선택 시 표시)
  - Genus Detail Modal (상세정보)

- **Phase 11 후속**: 데이터 정리 및 UI 개선
  - 트리뷰 각 노드에 상세정보 아이콘 추가
  - Author 필드 정리 (쉼표, 연도 뒤 각주 번호)
  - nov. 처리 → Adrain, 2011
  - genera_count 재계산 (실제 하위 Genus 수)
  - Genus 목록 유효성 필터 (Valid only 체크박스)
  - 트리뷰 Expand/Collapse All 버튼
  - Synonymy에서 senior taxon으로 이동 링크

- **Phase 12 완료**: Bibliography 테이블
  - Literature Cited 파싱 (2,130건)
  - article/book/chapter/cross_ref 분류
  - 연도 범위: 1745-2003

- **2026-02-06 UI 개선**
  - Rank 상세정보 Statistics 중복 표시 수정 (Genera/Genus)
  - Children 목록 클릭 네비게이션 (트리 펼침 + 상세정보 표시)

- **Phase 13 완료**: SCODA-Core 메타데이터 (**브랜치: `feature/scoda-implementation`**)
  - artifact_metadata 테이블 (7건: identity, version, license 등)
  - provenance 테이블 (3건: Jell & Adrain 2002, Adrain 2011, build pipeline)
  - schema_descriptions 테이블 (90건: 모든 테이블/컬럼 설명)
  - API: `GET /api/metadata`, `GET /api/provenance`

- **Phase 14 완료**: Display Intent + Saved Queries
  - ui_display_intent 테이블 (6건: genera→tree/table, references→table 등)
  - ui_queries 테이블 (14건: taxonomy_tree, family_genera, genera_list 등)
  - API: `GET /api/display-intent`, `GET /api/queries`, `GET /api/queries/<name>/execute`
  - 테스트: 63개 (기존 47 + 신규 16)

- **Phase 15 완료**: UI Manifest (선언적 뷰 정의)
  - ui_manifest 테이블 (1건: default 매니페스트)
  - 6개 뷰 정의: taxonomy_tree, genera_table, genus_detail, references_table, formations_table, countries_table
  - API: `GET /api/manifest`
  - 프론트엔드: 뷰 탭 바, 범용 테이블 렌더러 (정렬/검색), tree↔table 뷰 전환
  - 테스트: 79개 (기존 63 + 신규 16)

- **Phase 16 완료**: 릴리스 메커니즘
  - `scripts/release.py`: 릴리스 패키징 스크립트 (SHA-256 + metadata.json + README)
  - SCODA 불변성 원칙: 기존 릴리스 덮어쓰기 불가
  - `--dry-run` 모드 지원
  - `releases/` 디렉토리 `.gitignore`에 추가
  - 테스트: 91개 (기존 79 + 신규 12)

- **Phase 17 완료**: Local Overlay (사용자 주석)
  - `user_annotations` 테이블: 사용자 주석 저장 (note, correction, alternative, link)
  - 6개 entity_type 지원: genus, family, order, suborder, superfamily, class
  - API: `GET /api/annotations/<type>/<id>`, `POST /api/annotations`, `DELETE /api/annotations/<id>`
  - 프론트엔드: My Notes 섹션 (Genus/Rank detail 모달, 노란 배경으로 시각적 구분)
  - SCODA 원칙: canonical 데이터 불변, 사용자 의견은 별도 레이어
  - 테스트: 101개 (기존 91 + 신규 10)

- **Phase 18 완료**: 독립 실행형 앱 (PyInstaller)
  - `scripts/serve.py`: Flask 서버 런처 (브라우저 자동 오픈)
  - `trilobase.spec`: PyInstaller 빌드 설정
  - `scripts/build.py`: 빌드 자동화 스크립트
  - Windows/Linux onefile 빌드 지원 (13-15MB)
  - DB/templates/static 자동 번들링

- **Phase 19 완료**: GUI 컨트롤 패널
  - `scripts/gui.py`: tkinter 기반 GUI (420x320px)
  - Start/Stop/Open Browser/Exit 버튼
  - DB 경로, 서버 상태, URL 표시
  - 서버 시작 후 자동 브라우저 오픈
  - 콘솔 숨김 모드 (`console=False`)

- **Phase 20 완료**: Overlay DB 분리 (PyInstaller read-only 문제 해결)
  - Canonical DB: 실행 파일 내부 (read-only, 불변)
  - Overlay DB: 실행 파일 외부 (`trilobase_overlay.db`, read/write)
  - SQLite ATTACH로 이중 DB 연결
  - `overlay_metadata` 테이블: canonical 버전 추적
  - `entity_name` 컬럼 추가: 릴리스 간 annotation 매칭용
  - GUI에 Canonical + Overlay DB 정보 표시
  - 테스트: 101개 통과

- **Phase 21 완료**: GUI 로그 뷰어 + PyInstaller 호환성 수정
  - GUI 크기: 800x600 (리사이즈 가능)
  - Flask 로그 실시간 표시:
    - Frozen 모드(PyInstaller): threading + sys.stdout/stderr redirect
    - 개발 모드: subprocess로 Flask 실행
  - 색상별 로그 레벨: ERROR(빨강), WARNING(주황), INFO(파랑), SUCCESS(초록)
  - 로그 자동 감지: 200 OK→초록, Exception→빨강, Running on→파랑
  - Clear Log 버튼, 자동 스크롤, 1000줄 제한
  - PyInstaller 버그 수정:
    - Frozen 모드 중복 프로세스 방지 (subprocess → threading)
    - scripts 모듈 import 실패 → app.py에 overlay DB 생성 함수 inline
    - bytes/str 처리, stderr 로그 색상 자동 감지
  - Windows 환경 디버깅 용이성 대폭 향상

- **Phase 22 완료**: MCP Server (Model Context Protocol) (**브랜치: `feature/scoda-implementation`**)
  - 목표: LLM이 자연어로 Trilobase 쿼리 가능하도록 MCP 서버 구현
  - 계획 문서: `devlog/20260209_P14_phase22_mcp_wrapper.md`
  - 완료 로그: `devlog/20260209_022_phase22_mcp_server.md`
  - 완료:
    - ✅ `mcp_server.py` 구현 (729 lines, 14개 도구, stdio 모드)
    - ✅ Evidence Pack 패턴 구현 (raw_entry, fide, provenance 필드)
    - ✅ 버그 3개 수정 (중복 코드, fetchone 호출, bibliography 컬럼)
    - ✅ 테스트 작성 및 통과 (test_mcp_basic.py, test_mcp.py)
    - ✅ 의존성 추가 (`mcp>=1.0.0`, pytest, pytest-asyncio)
  - 14개 MCP 도구:
    - Taxonomy: get_taxonomy_tree, get_rank_detail, get_family_genera
    - Search: search_genera, get_genera_by_country, get_genera_by_formation
    - Metadata: get_metadata, get_provenance, list_available_queries
    - Queries: execute_named_query
    - Annotations: get_annotations, add_annotation, delete_annotation
    - Detail: get_genus_detail (Evidence Pack)
  - 주요 개념:
    - **DB is truth, MCP is access, LLM is narration**
    - LLM은 판단/정의 금지, 증거 기반 서술만 수행
    - Canonical DB 불변, Overlay DB를 통한 사용자 주석만 허용

- **Phase 23 완료**: MCP Server SSE 통합 (**브랜치: `feature/scoda-implementation`**)
  - 목표: MCP 서버를 GUI에 통합하여 Flask와 함께 SSE 모드로 자동 실행
  - 계획 문서: `devlog/20260210_P15_phase23_mcp_sse_integration.md`
  - 완료 로그: `devlog/20260210_023_phase23_mcp_sse_integration.md`
  - 완료:
    - ✅ SSE 모드 구현 (Starlette + Uvicorn, 포트 8081)
    - ✅ GUI 통합 (Flask + MCP 동시 시작/중지)
    - ✅ Health check 엔드포인트 (`/health`)
    - ✅ 하위 호환성 유지 (stdio 모드 계속 사용 가능)
    - ✅ PyInstaller spec 업데이트 (mcp_server.py 포함)
    - ✅ 의존성 추가 (`starlette`, `uvicorn`)
  - SSE 엔드포인트:
    - `GET /sse`: SSE 연결 (MCP 통신)
    - `POST /messages`: 메시지 전송
    - `GET /health`: 헬스체크

- **Phase 24 완료**: GUI MCP SSE 독립 실행 분리 (**브랜치: `feature/scoda-implementation`**)
  - 목표: GUI 기본 실행 시 Flask(8080)만 시작, MCP SSE(8081)는 별도 버튼으로 선택 실행
  - 계획 문서: `devlog/20260210_P17_gui_mcp_sse_optional.md`
  - 완료 로그: `devlog/20260210_024_phase24_gui_mcp_sse_optional.md`
  - 완료:
    - ✅ "Start All" → "Start Flask" / "Stop Flask" (Flask 전용)
    - ✅ "Start MCP SSE" / "Stop MCP SSE" 버튼 신규 추가
    - ✅ Flask와 MCP SSE 완전 독립 (서로 영향 없음)
    - ✅ `start_mcp()`, `stop_mcp()` 메서드 신규 추가
    - ✅ `_update_status()` Flask/MCP 버튼 상태 독립 관리
  - 동작:
    - Flask 종료해도 MCP SSE 계속 실행
    - MCP SSE 종료해도 Flask 계속 실행
    - 기본 실행 시 Flask만 시작 (MCP SSE는 필요 시 수동 시작)

- **2026-02-10 DB 파싱 오류 수정 및 누락 genus 추가**
  - taxonomic_ranks 파싱 오류 16건 수정 (`[sic]` 중첩 괄호, JELL nov. year, 인코딩 오류 등)
  - formations 테이블 잘못된 이름 5건 수정/삭제
  - genus_formations/genus_locations 연결 오류 수정
  - trilobite_genus_list.txt: Kaniniella/Melopetasus 줄에서 별도 genus 분리
  - Kanlingia (T. ZHANG, 1981), Memmatella (W. ZHANG et al., 1995) DB 추가
  - devlog: `devlog/20260210_029_parsing_error_fixes.md`

- **2026-02-10 GUI/MCP EXE 분리** (**브랜치: `feature/scoda-implementation`**)
  - GUI에서 MCP SSE 관련 UI 요소 제거 (Start/Stop MCP SSE 버튼, MCP 상태/URL 표시)
  - EXE 두 개로 분리:
    - `trilobase.exe` (`console=False`): GUI 전용, 콘솔 블로킹 없음
    - `trilobase_mcp.exe` (`console=True`): MCP stdio 전용, 인자 없이 실행
  - `gui.py` main() 단순화 (argparse/MCP 분기 제거)
  - `trilobase.spec` 두 개의 독립 EXE 블록으로 분리
  - Claude Desktop 설정: `"command": "trilobase_mcp.exe"` (args 불필요)

- **Phase 25 완료**: .scoda ZIP 패키지 포맷 도입 (**브랜치: `feature/scoda-package`**)
  - `.scoda` ZIP 기반 데이터 패키지 포맷 정의 (manifest.json + data.db + assets/)
  - `scoda_package.py`: 핵심 모듈 — ScodaPackage 클래스 + 중앙 집중 DB 접근 함수
  - `scripts/create_scoda.py`: DB→.scoda 패키징 스크립트 (`--dry-run` 지원)
  - DB 경로 중복 제거: 4개 파일(app.py, mcp_server.py, gui.py, serve.py) → `scoda_package.py` 한 곳
  - PyInstaller exe에서 DB 번들링 제거 (exe 크기 감소)
  - 배포 구조: `trilobase.exe` + `trilobase_mcp.exe` + `trilobase.scoda` (외부)
  - 하위 호환: `.scoda` 없으면 `trilobase.db` 직접 사용 (폴백)
  - 테스트: 111개 (기존 101 + ScodaPackage 10)

- **2026-02-12 countries 데이터 품질 정리**
  - 파싱 오류 1건, 중복/오타 병합 8건, 소문자 접두어 정규화 4건
  - 151 → 142개, devlog: `devlog/20260212_031_countries_data_quality.md`

- **Phase 26 완료**: COW 국가 데이터 도입
  - `cow_states` 테이블: COW State System Membership v2024 (244 레코드)
  - `country_cow_mapping` 테이블: Trilobase countries ↔ COW 매핑 (142건, 매핑률 96.5%)
  - 매핑 방법: exact(50) + manual(54) + prefix(33), unmappable(5)
  - `provenance` 테이블에 COW 출처 추가
  - COW CSV 원본: `vendor/cow/v2024/States2024/statelist2024.csv` (git 추적)
  - 스크립트: `scripts/import_cow.py` (`--dry-run`, `--report` 지원)
  - devlog: `devlog/20260212_032_phase26_cow_import.md`

- **Phase 27 완료**: Geographic Regions 계층 구조
  - `geographic_regions` 테이블: 계층형 지리 데이터 (60 countries + 502 regions = 562건)
  - `genus_locations.region_id` 추가: 4,841건 100% 매핑
  - API: `/api/country/<id>` 수정 (regions 리스트 포함), `/api/region/<id>` 신규
  - UI: Country > Region 클릭 가능 링크, Region detail 모달
  - Named query: `countries_list` 갱신, `regions_list` 신규
  - 테스트: 137개 (120 + 17 MCP)
  - devlog: `devlog/20260212_035_phase27_geographic_regions.md`

- **Phase 28 완료**: ICS Chronostratigraphic Chart 임포트 + temporal_ranges 매핑
  - `ics_chronostrat` 테이블: ICS 지질시대 178개 concept (GTS 2020, SKOS/RDF)
  - `temporal_ics_mapping` 테이블: temporal_ranges 28개 코드 ↔ ICS 매핑 (40행)
  - 매핑 타입: exact(18), aggregate(17), partial(5), unmappable(1=INDET)
  - 계층 구조: Super-Eon → Eon → Era → Period → Sub-Period → Epoch → Age
  - provenance, schema_descriptions 갱신
  - 스크립트: `scripts/import_ics.py` (rdflib, `--dry-run`/`--report` 지원)
  - 원본: `vendor/ics/gts2020/chart.ttl` (CC-BY 4.0)
  - 테스트: 146개 (129 + 17 MCP)
  - devlog: `devlog/20260212_036_phase28_ics_import.md`

- **2026-02-12 Web UI 상세 페이지 및 상호 링크**
  - Countries/Formations/Bibliography/All Genera 테이블 행 클릭 → 상세 모달
  - API 3개 추가: `/api/country/<id>`, `/api/formation/<id>`, `/api/bibliography/<id>`
  - 각 상세 모달에 연결된 genera 목록 (클릭 → genus detail)
  - Genus detail에서 countries/formations 역방향 링크 추가
  - Genus detail에 상위 분류군 전체 계층 표시 (Class→Order→...→Family, 클릭 가능)
  - Family 이상 분류군 author/year 필드 분리 (198건: "저자, 연도" → author/year 분리)
  - devlog: `devlog/20260212_033_web_detail_pages.md`

- **Phase 29 완료**: ICS Chronostratigraphy 웹 UI
  - Chronostratigraphy 테이블 탭 추가 (178행, color chip 렌더링)
  - `/api/chronostrat/<id>` 신규: 계층, 연대, 색상, 자식, 관련 genera
  - `/api/genus/<id>` 수정: `temporal_ics_mapping` 필드 추가 (temporal_code → ICS unit 링크)
  - `ics_chronostrat_list` named query + manifest 갱신
  - Genus detail Temporal Range: 원본 코드 유지 + ICS 매핑 링크 표시
  - 테스트: 145개 (기존 129 + 신규 16)
  - devlog: `devlog/20260212_037_phase29_ics_web_ui.md`


- **Phase 30 완료**: ICS Chronostratigraphic Chart 뷰
  - Chronostratigraphy 탭: 플랫 테이블 → ICS 스타일 계층형 색상 테이블
  - 7컬럼: Eon | Era | Period | Sub-Period | Epoch | Age | Age(Ma)
  - 117 leaf 행, rowspan/colspan 중첩, ICS 지정 색상 배경
  - 특수 처리: Super-Eon 승격, Pridoli gap 보정, Hadean 전체 span
  - 매니페스트 type "chart", 쿼리에 parent_id 추가
  - 테스트: 147개 (기존 145 + 신규 2)
  - devlog: `devlog/20260212_038_phase30_ics_chart_view.md`

- **PaleoCore 스키마 설계 완료** (설계 문서)
  - PaleoCore/Trilobase 패키지 분리 스키마 정의서 작성
  - 20개 테이블 → PaleoCore(8), Trilobase(6), Both(6) 분류
  - PaleoCore: 14개 테이블 CREATE TABLE SQL 정의 (8 데이터 + 6 SCODA 메타)
  - manifest.json, SCODA 메타데이터 정의
  - Logical Foreign Key 명세 (cross-package 참조 4건)
  - 계획 문서: `devlog/20260213_P27_paleocore_schema.md`
  - 정의서: `docs/paleocore_schema.md`

- **Phase 31 완료**: PaleoCore DB 생성 스크립트
  - `scripts/create_paleocore.py`: trilobase.db → paleocore.db 추출 스크립트
  - 8개 데이터 테이블 (3,340 레코드) + 6개 SCODA 메타데이터 테이블 (14개 총)
  - `taxa_count` 컬럼 제거 (countries, geographic_regions, formations)
  - SCODA 메타: artifact_metadata 7건, provenance 3건, schema_descriptions 88건, ui 13건
  - `--dry-run`, `--source`, `--output` 옵션 지원
  - paleocore.db: 328 KB, FK integrity 0 errors
  - devlog: `devlog/20260213_039_paleocore_db_creation.md`

- **Phase 32 완료**: Dual-DB 운영 (PaleoCore ATTACH)
  - `taxonomic_ranks`에서 레거시 컬럼 삭제 (`country_id`, `formation_id`) — 20→18 컬럼
  - `scoda_package.py`: paleocore.db를 `pc` alias로 ATTACH (자동 탐색)
  - `app.py`: `GET /api/paleocore/status` — cross-DB 검증 엔드포인트
  - 3개 DB 동시 운영: main(trilobase.db) + overlay + pc(paleocore.db)
  - Cross-DB JOIN 정상: genus_locations↔pc.countries, genus_formations↔pc.formations
  - 테스트: 164개 전부 통과
  - devlog: `devlog/20260213_040_phase32_dual_db.md`

- **Phase 33 완료**: PaleoCore 쿼리 `pc.*` prefix 전환
  - `app.py`: 16개 쿼리에서 PaleoCore 테이블을 `pc.*` prefix로 전환
    - formations → pc.formations, geographic_regions → pc.geographic_regions
    - ics_chronostrat → pc.ics_chronostrat, temporal_ics_mapping → pc.temporal_ics_mapping
  - `mcp_server.py`: 6개 쿼리에서 PaleoCore 테이블을 `pc.*` prefix로 전환
    - formations → pc.formations, countries → pc.countries
  - `trilobase.db`: ui_queries의 ics_chronostrat_list SQL 업데이트
  - `test_app.py`: test paleocore DB 생성 fixture 추가, 3-tuple 언패킹 전환
  - 테스트: 164개 전부 통과
  - devlog: `devlog/20260213_041_phase33_pc_prefix.md`

- **Phase 34 완료**: trilobase.db에서 PaleoCore 테이블 DROP
  - trilobase.db에서 8개 PaleoCore 테이블 DROP (3,340 레코드)
    - country_cow_mapping, cow_states, temporal_ics_mapping, ics_chronostrat
    - geographic_regions, formations, countries, temporal_ranges
  - ui_queries 6개 SQL `pc.*` prefix 업데이트 (genus_formations, genus_locations, formations_list, countries_list, genera_by_country, regions_list)
  - schema_descriptions 49행 삭제 (143 → 94행)
  - `scripts/release.py`: formations/countries 통계 제거
  - `test_app.py`: canonical DB fixture 정리, TestICSChronostrat → paleocore_db 전환
  - 테스트: 164개 전부 통과
  - devlog: `devlog/20260213_042_phase34_drop_paleocore_tables.md`

- **Phase 35 완료**: PaleoCore .scoda 패키지 + Dependency 반영
  - `ScodaPackage.create()` 범용화: taxonomic_ranks 하드코딩 제거, 모든 데이터 테이블 합산
  - `scripts/create_paleocore_scoda.py` 신규: paleocore.db → paleocore.scoda (93 KB, 3,340 records)
  - `scripts/create_scoda.py`: trilobase.scoda manifest에 paleocore dependency 선언
  - `scoda_package.py`: paleocore.scoda 우선 탐색 → paleocore.db 폴백
  - `scripts/create_paleocore.py`: 소스 테이블 부재 시 경고 메시지
  - 테스트: 169개 전부 통과 (기존 164 + 신규 5)
  - devlog: `devlog/20260213_043_phase35_paleocore_scoda.md`

- **Phase 36 완료**: 조합 .scoda 배포 테스트
  - TestCombinedScodaDeployment: .scoda 자동 탐색, 3-DB ATTACH, Cross-DB JOIN, Flask API, get_scoda_info (6개)
  - TestApiPaleocoreStatus: `/api/paleocore/status` 엔드포인트 기본 검증 (3개)
  - `_resolve_paleocore()` .scoda 우선 탐색 / .db 폴백 검증
  - 두 .scoda에서 추출한 DB로 genus detail API pc.formations/pc.geographic_regions JOIN 검증
  - 테스트: 178개 전부 통과 (기존 169 + 신규 9, MCP 17개 포함)
  - devlog: `devlog/20260213_044_phase36_combined_scoda_test.md`

- **Phase 37 완료**: PyInstaller 빌드에 paleocore.scoda 포함
  - `scripts/build.py`: `create_paleocore_scoda_package()` 함수 추가
  - 빌드 시 `dist/trilobase.scoda` + `dist/paleocore.scoda` 동시 생성
  - `paleocore.db` 없으면 skip (에러 아님, trilobase 독립 동작 가능)
  - 배포 안내 메시지에 `paleocore.scoda` 포함
  - devlog: `devlog/20260213_045_phase37_build_paleocore_scoda.md`

- **Phase 38 완료**: GUI를 "SCODA Desktop"으로 리브랜딩
  - "Trilobase SCODA Viewer" → "SCODA Desktop" (타이틀, 헤더, 로그)
  - Information 섹션: "Packages:" + PaleoCore dependency 행 표시
  - 시작 로그: `Loaded: trilobase.scoda` + `└ dependency: paleocore.scoda` 형식
  - `scoda_package.py`: `get_scoda_info()`에 paleocore_version/name/record_count 추가
  - devlog: `devlog/20260213_046_phase38_scoda_desktop_rebranding.md`

- **2026-02-13 Bugfix**: taxa_count 컬럼 참조 제거
  - Phase 34 DROP 이후 `app.py` 3개 엔드포인트에서 `taxa_count` 컬럼 참조 → 500 에러
  - `/api/country/<id>`, `/api/region/<id>`, `/api/formation/<id>` 수정
  - `COUNT(DISTINCT)` JOIN으로 실시간 계산하도록 대체
  - devlog: `devlog/20260213_047_fix_taxa_count_column.md`

- **2026-02-13 Bugfix**: ui_queries의 taxa_count 컬럼 참조 오류
  - Countries/Formations 탭 "Error loading data" — Flask 로그 없음 (400 JSON 응답이라 로그 미출력)
  - `ui_queries` 테이블의 `countries_list`, `formations_list` SQL이 제거된 `taxa_count` 컬럼 참조
  - `JOIN + COUNT(DISTINCT)`로 실시간 계산하도록 SQL 업데이트
  - devlog: `devlog/20260213_048_fix_named_query_taxa_count.md`

### 데이터베이스 현황

#### taxonomic_ranks (통합 테이블)

| Rank | 개수 |
|------|------|
| Class | 1 |
| Order | 12 |
| Suborder | 8 |
| Superfamily | 13 |
| Family | 191 |
| Genus | 5,115 |
| **총계** | **5,340** |

#### Genus 통계

| 항목 | 값 | 비율 |
|------|-----|------|
| 유효 Genus | 4,260 | 83.3% |
| 무효 Genus | 855 | 16.7% |
| Synonym 연결됨 | 1,031 | 97.6% |
| Country 연결됨 | 4,841 | 99.9% |
| Formation 연결됨 | 4,853 | 99.9% |

#### 테이블 목록

**Canonical DB (trilobase.db) — Read-only, 불변:**

| 테이블/뷰 | 레코드 수 | 설명 |
|-----------|----------|------|
| taxonomic_ranks | 5,340 | 통합 분류 체계 (Class~Genus) |
| synonyms | 1,055 | 동의어 관계 |
| genus_formations | 4,853 | Genus-Formation 다대다 관계 |
| genus_locations | 4,841 | Genus-Country 다대다 관계 |
| bibliography | 2,130 | 참고문헌 (Literature Cited) |
| taxa (뷰) | 5,113 | 하위 호환성 뷰 |
| artifact_metadata | 7 | SCODA 아티팩트 메타데이터 |
| provenance | 5 | 데이터 출처 |
| schema_descriptions | 94 | 테이블/컬럼 설명 |
| ui_display_intent | 6 | SCODA 뷰 타입 힌트 |
| ui_queries | 16 | Named SQL 쿼리 |
| ui_manifest | 1 | 선언적 뷰 정의 (JSON) |

**Overlay DB (trilobase_overlay.db) — Read/write, 사용자 로컬 데이터:**

| 테이블 | 레코드 수 | 설명 |
|--------|----------|------|
| overlay_metadata | 2 | Canonical DB 버전 추적 (canonical_version, created_at) |
| user_annotations | 0 | 사용자 주석 (Local Overlay, Phase 17) |

### 파일 구조

```
trilobase/
├── trilobase.exe                     # GUI 뷰어 (console=False, dist/ 빌드 결과)
├── trilobase_mcp.exe                 # MCP stdio 서버 (console=True, dist/ 빌드 결과)
├── trilobase.db                      # Canonical SQLite DB
├── trilobase_overlay.db              # Overlay DB (사용자 주석, Phase 20)
├── trilobite_genus_list.txt          # 정제된 genus 목록
├── trilobite_genus_list_original.txt # 원본 백업
├── adrain2011.txt                    # Order 통합을 위한 suprafamilial taxa 목록
├── scoda_package.py                  # .scoda 패키지 + 중앙 DB 접근 (Phase 25)
├── app.py                            # Flask 웹 앱
├── mcp_server.py                     # MCP 서버 (Phase 22-23, stdio/SSE 모드)
├── templates/
│   └── index.html                    # 메인 페이지
├── static/
│   ├── css/style.css                 # 스타일
│   └── js/app.js                     # 프론트엔드 로직
├── test_app.py                      # pytest 테스트 (161개)
├── test_mcp_basic.py                # MCP 기본 테스트 (1개)
├── test_mcp.py                      # MCP 포괄적 테스트 (16개, asynccontextmanager 방식)
├── pytest.ini                       # pytest 설정 (asyncio_mode=auto)
├── conftest.py                      # anyio 백엔드 설정 (asyncio)
├── trilobase.spec                   # PyInstaller 빌드 설정 (Phase 18)
├── scripts/
│   ├── normalize_lines.py
│   ├── create_database.py
│   ├── normalize_database.py
│   ├── fix_synonyms.py
│   ├── normalize_families.py
│   ├── populate_taxonomic_ranks.py
│   ├── add_scoda_tables.py          # Phase 13: SCODA-Core 마이그레이션
│   ├── add_scoda_ui_tables.py       # Phase 14: Display Intent/Queries 마이그레이션
│   ├── add_scoda_manifest.py        # Phase 15: UI Manifest 마이그레이션
│   ├── release.py                   # Phase 16: 릴리스 패키징 스크립트
│   ├── add_user_annotations.py      # Phase 17: 사용자 주석 마이그레이션
│   ├── init_overlay_db.py           # Phase 20: Overlay DB 초기화
│   ├── serve.py                     # Phase 18: Flask 서버 런처
│   ├── gui.py                       # Phase 19: GUI 컨트롤 패널
│   ├── build.py                     # Phase 18/37: 빌드 자동화 (trilobase.scoda + paleocore.scoda)
│   ├── create_scoda.py              # Phase 25: .scoda 패키지 생성
│   ├── import_cow.py               # Phase 26: COW 국가 데이터 임포트
│   ├── fix_countries_quality.py    # countries 데이터 품질 정리
│   ├── create_geographic_regions.py # Phase 27: Geographic Regions 마이그레이션
│   ├── import_ics.py              # Phase 28: ICS 지층 연대표 임포트
│   ├── create_paleocore.py       # Phase 31: PaleoCore DB 생성
│   └── create_paleocore_scoda.py # Phase 35: PaleoCore .scoda 패키지 생성
├── devlog/
│   ├── 20260204_P01~P05_*.md        # Phase 계획 문서
│   ├── 20260204_001~011_*.md        # Phase 1-11 완료 로그
│   ├── 20260207_P07~P12_*.md        # SCODA 계획 문서
│   ├── 20260207_012~020_*.md        # Phase 13-20 완료 로그
│   ├── 20260208_P13_*.md            # Phase 21 계획 문서
│   ├── 20260208_021_*.md            # Phase 21 완료 로그
│   ├── 20260209_P14_*.md            # Phase 22 계획 문서
│   ├── 20260209_022_*.md            # Phase 22 완료 로그
│   └── 20260207_R01~R02_*.md        # 리뷰 문서
├── vendor/
│   ├── cow/v2024/States2024/statelist2024.csv  # COW v2024 원본 CSV
│   └── ics/gts2020/chart.ttl                   # ICS GTS 2020 (SKOS/RDF)
├── docs/
│   ├── HANDOVER.md                  # 인수인계 문서 (프로젝트 현황)
│   ├── RELEASE_GUIDE.md             # 릴리스 및 배포 가이드 (버전 관리)
│   ├── SCODA_CONCEPT.md             # SCODA 개념 설명
│   └── paleocore_schema.md          # PaleoCore 패키지 스키마 정의서 (설계)
└── CLAUDE.md
```

## SCODA 구현 + 배포 완료 (브랜치: `feature/scoda-implementation`)

Trilobase를 SCODA(Self-Contained Data Artifact) 참조 구현으로 전환하고 독립 실행형 앱으로 패키징 완료.
상세 계획: `devlog/20260207_P07_scoda_implementation.md`

| Phase | 내용 | 상태 |
|-------|------|------|
| Phase 13 | SCODA-Core 메타데이터 (Identity, Provenance, Semantics) | ✅ 완료 |
| Phase 14 | Display Intent + Saved Queries | ✅ 완료 |
| Phase 15 | UI Manifest (선언적 뷰 정의) | ✅ 완료 |
| Phase 16 | 릴리스 메커니즘 (버전 태깅, 패키징) | ✅ 완료 |
| Phase 17 | Local Overlay (사용자 주석) | ✅ 완료 |
| Phase 18 | 독립 실행형 앱 (PyInstaller) | ✅ 완료 |
| Phase 19 | GUI 컨트롤 패널 (tkinter) | ✅ 완료 |
| Phase 20 | Overlay DB 분리 (read-only 문제 해결) | ✅ 완료 |
| Phase 21 | GUI 로그 뷰어 (디버깅 지원) | ✅ 완료 |
| Phase 22 | MCP Server (LLM 자연어 쿼리 지원) | ✅ 완료 |
| Phase 23 | MCP Server SSE 통합 (GUI 통합) | ✅ 완료 |
| Phase 25 | .scoda ZIP 패키지 포맷 + DB-앱 분리 | ✅ 완료 |
| Phase 26 | COW 국가 데이터 도입 (countries ↔ COW 매핑) | ✅ 완료 |
| Phase 27 | Geographic Regions 계층 구조 (country/region 분리) | ✅ 완료 |
| Phase 28 | ICS Chronostratigraphic Chart 임포트 + temporal_ranges 매핑 | ✅ 완료 |
| Phase 29 | ICS Chronostratigraphy 웹 UI (테이블 탭 + detail 모달 + genus 링크) | ✅ 완료 |
| Phase 30 | ICS Chart 뷰 (계층형 색상 코딩 테이블) | ✅ 완료 |

## 테스트 현황

| 파일 | 테스트 수 | 상태 |
|------|---------|------|
| `test_app.py` | 161개 | ✅ 통과 |
| `test_mcp_basic.py` | 1개 | ✅ 통과 |
| `test_mcp.py` | 16개 | ✅ 통과 |
| **합계** | **178개** | **✅ 전부 통과** |

**실행 방법:**
```bash
pytest test_app.py test_mcp_basic.py test_mcp.py
# 의존성: pip install mcp pytest-asyncio
```

**pytest 설정 (`pytest.ini`):**
- `asyncio_mode = auto` — async 테스트 자동 인식
- `asyncio_default_fixture_loop_scope = function` — 독립 이벤트 루프
- `conftest.py` — anyio 백엔드를 asyncio로 명시

## 다음 작업

PaleoCore 분리 및 .scoda 패키징 완료 (Phase 31-37).
GUI "SCODA Desktop" 리브랜딩 완료 (Phase 38).
- PaleoCore 독립 뷰어 (paleocore.scoda를 단독으로 열어서 탐색)

## 미해결 항목

- Synonym 미연결 4건 (원본에 senior taxa 없음)
- Location/Formation 없는 taxa는 모두 무효 taxa (정상)
- parent_id NULL인 Genus 342건 (family 필드 자체가 NULL인 무효 taxa)

## 전체 계획

1. ~~Phase 1: 줄 정리~~ ✅
2. ~~Phase 2: 깨진 문자 및 오타 수정~~ ✅
3. ~~Phase 3: 데이터 검증~~ ✅
4. ~~Phase 4: DB 스키마 설계 및 데이터 임포트~~ ✅
5. ~~Phase 5: 정규화 (Formation, Location, Synonym)~~ ✅
6. ~~Phase 6: Family 정규화~~ ✅
7. ~~Phase 7: Order 통합~~ ✅
8. ~~Phase 8: Taxonomy Table Consolidation~~ ✅
9. ~~Phase 9: Taxa와 Taxonomic_ranks 통합~~ ✅
10. ~~Phase 10: Formation/Location Relation 테이블~~ ✅
11. ~~Phase 11: Web Interface~~ ✅
12. ~~Phase 12: Bibliography 테이블~~ ✅
13. ~~Phase 13: SCODA-Core 메타데이터~~ ✅ (브랜치: `feature/scoda-implementation`)
14. ~~Phase 14: Display Intent + Saved Queries~~ ✅
15. ~~Phase 15: UI Manifest~~ ✅
16. ~~Phase 16: 릴리스 메커니즘~~ ✅
17. ~~Phase 17: Local Overlay~~ ✅
18. ~~Phase 18: 독립 실행형 앱 (PyInstaller)~~ ✅
19. ~~Phase 19: GUI 컨트롤 패널~~ ✅
20. ~~Phase 20: Overlay DB 분리~~ ✅
21. ~~Phase 21: GUI 로그 뷰어~~ ✅
22. ~~Phase 22: MCP Server~~ ✅ (브랜치: `feature/scoda-implementation`)
23. ~~Phase 23: MCP Server SSE 통합~~ ✅ (브랜치: `feature/scoda-implementation`)
25. ~~Phase 25: .scoda ZIP 패키지 포맷~~ ✅ (브랜치: `feature/scoda-package`)
26. ~~Phase 26: COW 국가 데이터 도입~~ ✅
27. ~~Phase 27: Geographic Regions 계층 구조~~ ✅
28. ~~Phase 28: ICS Chronostratigraphic Chart 임포트~~ ✅
29. ~~Phase 29: ICS Chronostratigraphy 웹 UI~~ ✅
30. ~~Phase 30: ICS Chart 뷰 (계층형 색상 코딩 테이블)~~ ✅

## DB 스키마

### Canonical DB (trilobase.db)

```sql
-- taxonomic_ranks: 5,340 records - 통합 분류 체계 (Class~Genus)
taxonomic_ranks (
    id, name, rank, parent_id, author, year, year_suffix,
    genera_count, notes, created_at,
    -- Genus 전용 필드
    type_species, type_species_author, formation, location, family,
    temporal_code, is_valid, raw_entry
)

-- synonyms: 1,055 records - 동의어 관계
synonyms (id, junior_taxon_id, senior_taxon_name, senior_taxon_id,
          synonym_type, fide_author, fide_year, notes)

-- genus_formations: 4,853 records - Genus-Formation 다대다 관계
genus_formations (id, genus_id, formation_id, is_type_locality, notes)

-- genus_locations: 4,841 records - Genus-Country 다대다 관계
genus_locations (id, genus_id, country_id, region, is_type_locality, notes)

-- bibliography: 2,130 records - 참고문헌
bibliography (id, authors, year, year_suffix, title, journal, volume, pages,
              publisher, city, editors, book_title, reference_type, raw_entry)

-- taxa: 뷰 (하위 호환성)
CREATE VIEW taxa AS SELECT ... FROM taxonomic_ranks WHERE rank = 'Genus';

-- SCODA-Core 테이블
artifact_metadata (key, value)                    -- 아티팩트 메타데이터 (key-value)
provenance (id, source_type, citation, description, year, url)  -- 데이터 출처
schema_descriptions (table_name, column_name, description)      -- 스키마 설명

-- SCODA UI 테이블
ui_display_intent (id, entity, default_view, description, source_query, priority)  -- 뷰 힌트
ui_queries (id, name, description, sql, params_json, created_at)                   -- Named Query
ui_manifest (name, description, manifest_json, created_at)                         -- 선언적 뷰 정의 (JSON)

-- 참고: PaleoCore 테이블 8개는 Phase 34에서 DROP됨
-- countries, formations, geographic_regions, cow_states, country_cow_mapping,
-- temporal_ranges, ics_chronostrat, temporal_ics_mapping → paleocore.db (pc.* prefix)
```

### Overlay DB (trilobase_overlay.db) — Phase 20

```sql
-- overlay_metadata: Canonical DB 버전 추적
overlay_metadata (key, value)  -- canonical_version, created_at

-- user_annotations: 사용자 주석 (Phase 17, Phase 20에서 분리)
user_annotations (
    id, entity_type, entity_id, entity_name,  -- entity_name: 릴리스 간 매칭용
    annotation_type, content, author, created_at
)
```

**SQLite ATTACH 사용 (3-DB):**
```python
conn = sqlite3.connect('trilobase.db')  # Canonical DB
conn.execute("ATTACH DATABASE 'trilobase_overlay.db' AS overlay")
conn.execute("ATTACH DATABASE 'paleocore.db' AS pc")

# Canonical 테이블 접근: SELECT * FROM taxonomic_ranks
# Overlay 테이블 접근: SELECT * FROM overlay.user_annotations
# PaleoCore 테이블 접근: SELECT * FROM pc.countries
# Cross-DB JOIN: SELECT ... FROM genus_locations gl JOIN pc.countries c ON gl.country_id = c.id
```

## DB 사용법

```bash
# 기본 쿼리 (taxa 뷰 사용)
sqlite3 trilobase.db "SELECT * FROM taxa LIMIT 10;"

# 전체 계층 구조 조회
sqlite3 trilobase.db "SELECT g.name, f.name as family, o.name as 'order'
FROM taxonomic_ranks g
LEFT JOIN taxonomic_ranks f ON g.parent_id = f.id
LEFT JOIN taxonomic_ranks sf ON f.parent_id = sf.id
LEFT JOIN taxonomic_ranks o ON sf.parent_id = o.id
WHERE g.rank = 'Genus' AND g.is_valid = 1 LIMIT 10;"

# Genus의 Formation 조회 (relation 테이블 사용)
sqlite3 trilobase.db "SELECT g.name, f.name as formation
FROM taxonomic_ranks g
JOIN genus_formations gf ON g.id = gf.genus_id
JOIN formations f ON gf.formation_id = f.id
WHERE g.name = 'Paradoxides';"

# 특정 국가의 Genus 조회 (relation 테이블 사용)
sqlite3 trilobase.db "SELECT g.name, gl.region
FROM taxonomic_ranks g
JOIN genus_locations gl ON g.id = gl.genus_id
JOIN countries c ON gl.country_id = c.id
WHERE c.name = 'China' LIMIT 10;"
```

## 주의사항

- `trilobite_genus_list.txt`가 항상 최신 텍스트 버전
- `trilobase.db`가 최신 데이터베이스
- 각 Phase 완료 시 git commit
- 원본 PDF 필요 시: Jell & Adrain (2002)
