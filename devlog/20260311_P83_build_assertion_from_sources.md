# P83: Assertion DB 0.2.0 — Source 파일 기반 빌드

**Date:** 2026-03-11
**Type:** Plan

## 목표

`data/sources/*.txt` (R04 확장 형식)를 **단일 진입점**으로 사용하여
assertion DB 0.2.0을 빌드하는 `scripts/build_assertion_db.py` 작성.

기존 3단계 파이프라인(`create_assertion_db.py` → `import_treatise1959.py` → `import_treatise.py`)을
하나의 스크립트로 통합한다.

## 현재 파이프라인 (0.1.x)

```
canonical DB (trilobase-0.2.6.db)
    ↓ create_assertion_db.py
    ├── taxon 복사 (5,341 → 5,604 with placeholders)
    ├── reference 복사 (bibliography 2,131 + JA2002/Adrain refs)
    ├── assertions 생성 (parent_id → PLACED_IN, opinions → SYNONYM_OF)
    ├── default profile 빌드
    └── junction tables 복사
    ↓ import_treatise1959.py
    ├── treatise_1959_taxonomy.json 파싱 (fuzzy match)
    ├── assertions + treatise1959 profile
    ↓ import_treatise.py
    ├── treatise_ch4/ch5_taxonomy.json 파싱
    └── assertions + treatise2004 profile (hybrid)
```

**문제점:**
- JSON 중간 형식 의존 (OCR → JSON → DB)
- 3개 스크립트 순서 의존
- canonical DB의 parent_id → assertion 변환이 이중 작업
- Fuzzy matching 불필요 (source 파일에 정제된 이름 사용)

## 새 파이프라인 (0.2.0)

```
data/sources/*.txt (R04 확장 형식)
    ↓ build_assertion_db.py (단일 스크립트)
    ├── Phase 1: 소스 파싱 → taxa + assertions 추출
    ├── Phase 2: taxon 테이블 구축
    ├── Phase 3: assertion 테이블 구축
    ├── Phase 4: classification profiles + edge caches 빌드
    ├── Phase 5: canonical DB에서 보조 데이터 복사
    └── Phase 6: SCODA 메타데이터 + 매니페스트

canonical DB (trilobase-0.2.6.db) → 보조 데이터만 제공:
  - reference/bibliography (2,131건)
  - genus_formations (4,503건)
  - genus_locations (4,849건)
  - taxon_reference (4,173건)
  - taxon 메타데이터 (formation, location, temporal_code, type_species 등)
```

## 소스 파일별 역할

| 소스 파일 | 제공 데이터 | 프로필 |
|-----------|------------|--------|
| jell_adrain_2002.txt | 속(genus) 목록, 과(family) 배정, 동의어 | default |
| adrain_2011.txt | 상위 분류 계층 (목→과) | default |
| treatise_1959.txt | 전체 계층 (목→속) | treatise1959 |
| treatise_2004_ch4.txt | Agnostida 계층 | treatise2004 |
| treatise_2004_ch5.txt | Redlichiida 계층 | treatise2004 |

## 처리 파이프라인 상세

### Phase 1: 소스 파싱

각 소스 파일에 대해:
1. YAML 헤더 파싱 → reference 정보, scope 추출
2. 계층 본문 파싱 → `(parent, child, rank, authority, year, status)` 튜플 리스트
3. 동의어/spelling 마커 파싱 → `(subject, predicate, object, type)` 튜플 리스트

**파서 공통 로직:**
- 들여쓰기 → 부모-자식 관계 결정
- Rank 키워드: `Order`, `Suborder`, `Superfamily`, `Family`, `Subfamily` → rank 결정
- rank 키워드 없으면 → genus (JA2002) 또는 컨텍스트에 따라 결정
- `?` prefix → questionable status
- `[incertae sedis]` → incertae_sedis status
- `#` 으로 시작하는 줄 → 코멘트 (무시)
- `= Target (j.s.s.)` → SYNONYM_OF assertion
- `~ Target (spelling)` → SPELLING_OF assertion

### Phase 2: Taxon 테이블 구축

1. **기본 taxa**: canonical DB에서 모든 taxon 복사 (metadata 보존)
   - id, name, rank, author, year, formation, location, temporal_code 등
2. **신규 taxa**: 소스 파일에만 있는 분류군 추가
   - Treatise 파일의 신규 subfamily/superfamily 등
   - `is_placeholder=1` for uncertain containers
3. **이름 매칭**: 소스 파일의 taxon name → DB taxon id 매핑
   - 정확 매칭 (name + rank)
   - 동명이류 처리: 같은 이름 + 다른 rank → 별도 taxon

### Phase 3: Assertion 테이블 구축

소스별 assertion 생성:

**JA2002 (default 프로필용):**
- 각 genus → Family: `PLACED_IN` (reference: JA2002)
- `?` genus → Family: `PLACED_IN` (questionable)
- `= Target` → `SYNONYM_OF`
- `~ Target` → `SPELLING_OF`

**Adrain 2011 (default 프로필용):**
- 상위 분류 계층: Family → Superfamily → Suborder → Order → Trilobita
- `PLACED_IN` assertions (reference: Adrain 2011)

**Treatise 1959:**
- 전체 계층: `PLACED_IN` assertions (reference: Moore 1959)

**Treatise 2004 ch4/ch5:**
- Agnostida/Redlichiida 계층: `PLACED_IN` assertions

**is_accepted 결정:**
- Default 프로필 소스 (JA2002 + Adrain 2011)의 assertions → `is_accepted=1`
- Treatise 소스의 assertions → `is_accepted=0` (프로필별 edge cache로 사용)

### Phase 4: Classification Profiles + Edge Caches

**Profile 1: default**
- Source: JA2002 (genus→family) + Adrain 2011 (family→order→class)
- Edge cache: `is_accepted=1`인 PLACED_IN assertions에서 직접 생성

**Profile 2: treatise1959**
- Source: treatise_1959.txt의 모든 PLACED_IN
- Standalone profile (default와 독립)

**Profile 3: treatise2004**
- Base: treatise1959 edges 복사
- Override: Treatise 2004 ch4/ch5 assertions로 교체
  - Agnostida subtree: ch4 assertions로 전면 교체
  - Redlichiida subtree: ch5 assertions로 전면 교체
- comprehensive scope에 따른 removal 적용 (R03)

### Phase 5: 보조 데이터 복사

Canonical DB에서:
- `reference` (bibliography 2,131건 + 소스별 reference 추가)
- `genus_formations` (4,503건)
- `genus_locations` (4,849건)
- `taxon_reference` (4,173건)

### Phase 6: SCODA 메타데이터

기존 `create_assertion_db.py`의 메타데이터 로직 재사용:
- `artifact_metadata`, `provenance`, `schema_descriptions`
- `ui_queries` (46개), `ui_manifest`, `ui_display_intent`
- 호환성 뷰: `v_taxonomy_tree`, `v_taxonomic_ranks`, `synonyms`

## 기존 스크립트 대비 변경점

| 항목 | 0.1.x | 0.2.0 |
|------|-------|-------|
| 진입점 | 3개 스크립트 순차 실행 | 단일 스크립트 |
| 데이터 소스 | canonical DB + JSON | source TXT + canonical DB(보조) |
| Fuzzy matching | 필요 (OCR 오류) | 불필요 (정제된 소스) |
| 프로필 빌드 | 증분 추가 | 일괄 빌드 |
| Treatise 2004 | hybrid (copy + replace) | comprehensive removal 적용 |
| 동의어 소스 | canonical DB opinions | JA2002 source 파일 |

## 검증 기준 (validate 통과 조건)

- taxon 수 ≥ 5,600
- PLACED_IN assertions ≥ 6,800
- SYNONYM_OF assertions ≥ 1,000
- 3개 프로필 존재
- 각 프로필의 Order 수 > 0
- default profile edges ≥ 5,000
- treatise1959 profile edges ≥ 1,300
- treatise2004 profile edges ≥ 1,300

## 파일 구조

```
scripts/
├── build_assertion_db.py      ← NEW (단일 빌드 스크립트)
├── create_assertion_db.py     ← 유지 (0.1.x 호환)
├── import_treatise1959.py     ← 유지 (0.1.x 호환)
├── import_treatise.py         ← 유지 (0.1.x 호환)
└── validate_assertion_db.py   ← 재사용
```

## 구현 순서

1. 소스 파서 구현 (헤더 + 계층 본문)
2. taxon 구축 (canonical DB 복사 + 소스 신규 taxa)
3. assertion 구축 (소스별 PLACED_IN + SYNONYM_OF)
4. profile + edge cache 빌드
5. 보조 데이터 복사 + SCODA 메타데이터
6. 검증 실행
