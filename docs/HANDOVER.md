# Trilobase 프로젝트 Handover

**마지막 업데이트:** 2026-02-10

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
  - 주요 개선:
    - DB 연결 유지 → 빠른 응답
    - 원클릭 시작 ("Start All" 버튼)
    - 통합 로그 뷰어 (Flask + MCP)

### 데이터베이스 현황

#### taxonomic_ranks (통합 테이블)

| Rank | 개수 |
|------|------|
| Class | 1 |
| Order | 12 |
| Suborder | 8 |
| Superfamily | 13 |
| Family | 191 |
| Genus | 5,113 |
| **총계** | **5,338** |

#### Genus 통계

| 항목 | 값 | 비율 |
|------|-----|------|
| 유효 Genus | 4,258 | 83.3% |
| 무효 Genus | 855 | 16.7% |
| Synonym 연결됨 | 1,031 | 97.7% |
| Country 연결됨 | 4,841 | 99.9% |
| Formation 연결됨 | 4,854 | 100% |

#### 테이블 목록

**Canonical DB (trilobase.db) — Read-only, 불변:**

| 테이블/뷰 | 레코드 수 | 설명 |
|-----------|----------|------|
| taxonomic_ranks | 5,338 | 통합 분류 체계 (Class~Genus) |
| synonyms | 1,055 | 동의어 관계 |
| genus_formations | 4,854 | Genus-Formation 다대다 관계 |
| genus_locations | 4,841 | Genus-Country 다대다 관계 |
| formations | 2,009 | 지층 정보 |
| countries | 151 | 국가 정보 |
| temporal_ranges | 28 | 지질시대 코드 |
| bibliography | 2,130 | 참고문헌 (Literature Cited) |
| taxa (뷰) | 5,113 | 하위 호환성 뷰 |
| artifact_metadata | 7 | SCODA 아티팩트 메타데이터 |
| provenance | 3 | 데이터 출처 |
| schema_descriptions | 107 | 테이블/컬럼 설명 |
| ui_display_intent | 6 | SCODA 뷰 타입 힌트 |
| ui_queries | 14 | Named SQL 쿼리 |
| ui_manifest | 1 | 선언적 뷰 정의 (JSON) |

**Overlay DB (trilobase_overlay.db) — Read/write, 사용자 로컬 데이터:**

| 테이블 | 레코드 수 | 설명 |
|--------|----------|------|
| overlay_metadata | 2 | Canonical DB 버전 추적 (canonical_version, created_at) |
| user_annotations | 0 | 사용자 주석 (Local Overlay, Phase 17) |

### 파일 구조

```
trilobase/
├── trilobase.db                      # Canonical SQLite DB
├── trilobase_overlay.db              # Overlay DB (사용자 주석, Phase 20)
├── trilobite_genus_list.txt          # 정제된 genus 목록
├── trilobite_genus_list_original.txt # 원본 백업
├── adrain2011.txt                    # Order 통합을 위한 suprafamilial taxa 목록
├── app.py                            # Flask 웹 앱
├── mcp_server.py                     # MCP 서버 (Phase 22-23, 829 lines, stdio/SSE 모드)
├── templates/
│   └── index.html                    # 메인 페이지
├── static/
│   ├── css/style.css                 # 스타일
│   └── js/app.js                     # 프론트엔드 로직
├── test_app.py                      # pytest 테스트 (101개)
├── test_mcp_basic.py                # MCP 기본 테스트 (Phase 22)
├── test_mcp.py                      # MCP 포괄적 테스트 (Phase 22, 16개)
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
│   └── build.py                     # Phase 18: 빌드 자동화
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
├── docs/
│   ├── HANDOVER.md                  # 인수인계 문서 (프로젝트 현황)
│   ├── RELEASE_GUIDE.md             # 릴리스 및 배포 가이드 (버전 관리)
│   └── SCODA_CONCEPT.md             # SCODA 개념 설명
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

## DB 스키마

### Canonical DB (trilobase.db)

```sql
-- taxonomic_ranks: 5,338 records - 통합 분류 체계 (Class~Genus)
taxonomic_ranks (
    id, name, rank, parent_id, author, year, year_suffix,
    genera_count, notes, created_at,
    -- Genus 전용 필드
    type_species, type_species_author, formation, location, family,
    temporal_code, is_valid, raw_entry, country_id, formation_id
)

-- synonyms: 1,055 records - 동의어 관계
synonyms (id, junior_taxon_id, senior_taxon_name, senior_taxon_id,
          synonym_type, fide_author, fide_year, notes)

-- genus_formations: 4,854 records - Genus-Formation 다대다 관계
genus_formations (id, genus_id, formation_id, is_type_locality, notes)

-- genus_locations: 4,841 records - Genus-Country 다대다 관계
genus_locations (id, genus_id, country_id, region, is_type_locality, notes)

-- formations: 2,009 records
formations (id, name, normalized_name, formation_type, country, region, period, taxa_count)

-- countries: 151 records
countries (id, name, code, taxa_count)

-- temporal_ranges: 28 records
temporal_ranges (id, code, name, period, epoch, start_mya, end_mya)

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

**SQLite ATTACH 사용:**
```python
conn = sqlite3.connect('trilobase.db')  # Canonical DB
conn.execute("ATTACH DATABASE 'trilobase_overlay.db' AS overlay")

# Canonical 테이블 접근: SELECT * FROM taxonomic_ranks
# Overlay 테이블 접근: SELECT * FROM overlay.user_annotations
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
