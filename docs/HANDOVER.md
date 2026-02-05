# Trilobase 프로젝트 Handover

**마지막 업데이트:** 2026-02-05

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
  - taxa 테이블을 taxonomic_ranks로 마이그레이션
  - synonyms 테이블 ID 참조 업데이트
  - taxa 테이블 삭제 후 뷰로 대체 (하위 호환성)
  - 전체 계층 구조 단일 테이블로 관리

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
| formations | 2,009 | 지층 정보 |
| countries | 151 | 국가 정보 |
| temporal_ranges | 28 | 지질시대 코드 |
| taxa (뷰) | 5,113 | 하위 호환성 뷰 |

### 파일 구조

```
trilobase/
├── trilobase.db                      # SQLite 데이터베이스
├── trilobase_backup_20260205.db      # Phase 8 작업 전 백업
├── trilobase_backup_phase9.db        # Phase 9 작업 전 백업
├── trilobite_genus_list.txt          # 정제된 genus 목록
├── trilobite_genus_list_original.txt # 원본 백업
├── adrain2011.txt                    # Order 통합을 위한 suprafamilial taxa 목록
├── scripts/
│   ├── normalize_lines.py
│   ├── create_database.py
│   ├── normalize_database.py
│   ├── fix_synonyms.py
│   ├── normalize_families.py
│   └── populate_taxonomic_ranks.py
├── devlog/
│   ├── 20260204_P01_data_cleaning_plan.md
│   ├── 20260204_001_phase1_line_normalization.md
│   ├── 20260204_002_phase2_character_fixes.md
│   ├── 20260204_003_phase3_data_validation_summary.md
│   ├── 20260204_004_phase4_database_creation.md
│   ├── 20260204_005_phase5_normalization.md
│   ├── 20260204_006_phase6_family_normalization.md
│   ├── 20260205_P02_taxonomy_table_consolidation.md
│   ├── 20260205_008_phase8_taxonomy_consolidation_complete.md
│   ├── 20260205_P03_taxa_taxonomic_ranks_consolidation.md
│   └── 20260205_009_phase9_taxa_consolidation_complete.md
├── docs/
│   └── HANDOVER.md
└── CLAUDE.md
```

## 다음 작업

### Phase 10 예정: Formation/Location Relation 테이블
- `formation`, `location` 필드를 synonym처럼 별도의 relation 테이블로 분리
- 현재는 taxonomic_ranks에 텍스트로 저장되어 있음
- 다대다 관계 지원 (하나의 genus가 여러 formation/location에서 발견될 수 있음)

### 미해결 항목
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
10. Phase 10: Formation/Location Relation 테이블 (예정)

## DB 스키마

```sql
-- taxonomic_ranks: 5,338 records - 통합 분류 체계 (Class~Genus)
taxonomic_ranks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    rank TEXT NOT NULL,  -- Class, Order, Suborder, Superfamily, Family, Genus
    parent_id INTEGER,   -- FK → taxonomic_ranks.id (self-referential)
    author TEXT,
    year TEXT,
    year_suffix TEXT,
    genera_count INTEGER DEFAULT 0,  -- Family 이상
    taxa_count INTEGER DEFAULT 0,    -- Family 이상
    notes TEXT,
    created_at TIMESTAMP,

    -- Genus 전용 필드
    type_species TEXT,
    type_species_author TEXT,
    formation TEXT,
    location TEXT,
    family TEXT,
    temporal_code TEXT,
    is_valid INTEGER DEFAULT 1,
    raw_entry TEXT,
    country_id INTEGER,
    formation_id INTEGER,

    FOREIGN KEY (parent_id) REFERENCES taxonomic_ranks(id)
)

-- taxa: 뷰 (하위 호환성)
CREATE VIEW taxa AS
SELECT id, name, rank, parent_id as family_id, author, year, year_suffix,
       type_species, type_species_author, formation, location, family,
       temporal_code, is_valid, notes, raw_entry, created_at,
       country_id, formation_id
FROM taxonomic_ranks WHERE rank = 'Genus';

-- synonyms: 1,055 records
synonyms (id, junior_taxon_id, senior_taxon_name, senior_taxon_id,
          synonym_type, fide_author, fide_year, notes)

-- formations: 2,009 records
formations (id, name, normalized_name, formation_type,
            country, region, period, taxa_count)

-- countries: 151 records
countries (id, name, code, taxa_count)

-- temporal_ranges: 28 records
temporal_ranges (id, code, name, period, epoch, start_mya, end_mya)
```

## DB 사용법

```bash
# 기본 쿼리 (taxa 뷰 사용 - 하위 호환)
sqlite3 trilobase.db "SELECT * FROM taxa LIMIT 10;"

# 유효 genus만 조회
sqlite3 trilobase.db "SELECT * FROM taxa WHERE is_valid = 1;"

# rank별 조회
sqlite3 trilobase.db "SELECT * FROM taxonomic_ranks WHERE rank = 'Family';"

# 전체 계층 구조 조회 (Genus → Family → Superfamily → Order)
sqlite3 trilobase.db "SELECT g.name as genus, f.name as family, sf.name as superfamily, o.name as 'order'
FROM taxonomic_ranks g
LEFT JOIN taxonomic_ranks f ON g.parent_id = f.id
LEFT JOIN taxonomic_ranks sf ON f.parent_id = sf.id
LEFT JOIN taxonomic_ranks o ON sf.parent_id = o.id
WHERE g.rank = 'Genus' AND g.is_valid = 1 LIMIT 10;"

# Synonym 관계 조회
sqlite3 trilobase.db "SELECT tr1.name as junior, tr2.name as senior, s.synonym_type
FROM synonyms s
JOIN taxonomic_ranks tr1 ON s.junior_taxon_id = tr1.id
LEFT JOIN taxonomic_ranks tr2 ON s.senior_taxon_id = tr2.id
LIMIT 10;"
```

## 주의사항

- `trilobite_genus_list.txt`가 항상 최신 텍스트 버전
- `trilobase.db`가 최신 데이터베이스
- 각 Phase 완료 시 git commit
- 원본 PDF 필요 시: Jell & Adrain (2002)
