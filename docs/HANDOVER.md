# Trilobase 프로젝트 Handover

**마지막 업데이트:** 2026-02-07

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

- **Phase 17 완료**: Local Overlay (사용자 주석) — SCODA 구현 완성
  - `user_annotations` 테이블: 사용자 주석 저장 (note, correction, alternative, link)
  - 6개 entity_type 지원: genus, family, order, suborder, superfamily, class
  - API: `GET /api/annotations/<type>/<id>`, `POST /api/annotations`, `DELETE /api/annotations/<id>`
  - 프론트엔드: My Notes 섹션 (Genus/Rank detail 모달, 노란 배경으로 시각적 구분)
  - SCODA 원칙: canonical 데이터 불변, 사용자 의견은 별도 레이어
  - 테스트: 101개 (기존 91 + 신규 10)

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
| user_annotations | 0 | 사용자 주석 (Local Overlay) |

### 파일 구조

```
trilobase/
├── trilobase.db                      # SQLite 데이터베이스
├── trilobite_genus_list.txt          # 정제된 genus 목록
├── trilobite_genus_list_original.txt # 원본 백업
├── adrain2011.txt                    # Order 통합을 위한 suprafamilial taxa 목록
├── app.py                            # Flask 웹 앱
├── templates/
│   └── index.html                    # 메인 페이지
├── static/
│   ├── css/style.css                 # 스타일
│   └── js/app.js                     # 프론트엔드 로직
├── test_app.py                      # pytest 테스트 (101개)
├── Trilobase_as_SCODA.md            # SCODA 개념 문서
├── scripts/
│   ├── normalize_lines.py
│   ├── create_database.py
│   ├── normalize_database.py
│   ├── fix_synonyms.py
│   ├── normalize_families.py
│   ├── populate_taxonomic_ranks.py
│   ├── add_scoda_tables.py          # Phase 13: SCODA-Core 마이그레이션
│   ├── add_scoda_ui_tables.py      # Phase 14: Display Intent/Queries 마이그레이션
│   ├── add_scoda_manifest.py       # Phase 15: UI Manifest 마이그레이션
│   ├── release.py                 # Phase 16: 릴리스 패키징 스크립트
│   └── add_user_annotations.py   # Phase 17: 사용자 주석 마이그레이션
├── devlog/
│   ├── 20260204_P01_data_cleaning_plan.md
│   ├── 20260204_001~006_*.md         # Phase 1-6 로그
│   ├── 20260205_P02_taxonomy_table_consolidation.md
│   ├── 20260205_008_phase8_taxonomy_consolidation_complete.md
│   ├── 20260205_P03_taxa_taxonomic_ranks_consolidation.md
│   ├── 20260205_009_phase9_taxa_consolidation_complete.md
│   ├── 20260205_P04_formation_location_relations.md
│   ├── 20260205_010_phase10_formation_location_relations_complete.md
│   ├── 20260205_P05_web_interface.md
│   └── 20260205_011_phase11_web_interface_complete.md
├── docs/
│   └── HANDOVER.md
└── CLAUDE.md
```

## SCODA 구현 완료 (브랜치: `feature/scoda-implementation`)

Trilobase를 SCODA(Self-Contained Data Artifact) 참조 구현으로 전환 완료.
상세 계획: `devlog/20260207_P07_scoda_implementation.md`

| Phase | 내용 | 상태 |
|-------|------|------|
| Phase 13 | SCODA-Core 메타데이터 (Identity, Provenance, Semantics) | ✅ 완료 |
| Phase 14 | Display Intent + Saved Queries | ✅ 완료 |
| Phase 15 | UI Manifest (선언적 뷰 정의) | ✅ 완료 |
| Phase 16 | 릴리스 메커니즘 (버전 태깅, 패키징) | ✅ 완료 |
| Phase 17 | Local Overlay (사용자 주석) | ✅ 완료 |

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

## DB 스키마

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

-- Local Overlay 테이블
user_annotations (id, entity_type, entity_id, annotation_type, content, author, created_at)  -- 사용자 주석
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
