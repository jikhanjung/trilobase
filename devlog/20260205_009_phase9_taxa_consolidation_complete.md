# Phase 9: Taxa와 Taxonomic_ranks 통합 완료

**날짜:** 2026-02-05

## 목표

`taxa`와 `taxonomic_ranks` 테이블을 통합하여 Class → Order → Suborder → Superfamily → Family → Genus 전체 계층을 단일 테이블로 관리

## 작업 수행 내역

### Step 1: 데이터베이스 백업
```bash
cp trilobase.db trilobase_backup_phase9.db
```

### Step 2: taxonomic_ranks 컬럼 확장

taxa 테이블의 모든 컬럼을 taxonomic_ranks에 추가:

```sql
ALTER TABLE taxonomic_ranks ADD COLUMN year_suffix TEXT;
ALTER TABLE taxonomic_ranks ADD COLUMN type_species TEXT;
ALTER TABLE taxonomic_ranks ADD COLUMN type_species_author TEXT;
ALTER TABLE taxonomic_ranks ADD COLUMN formation TEXT;
ALTER TABLE taxonomic_ranks ADD COLUMN location TEXT;
ALTER TABLE taxonomic_ranks ADD COLUMN temporal_code TEXT;
ALTER TABLE taxonomic_ranks ADD COLUMN is_valid INTEGER DEFAULT 1;
ALTER TABLE taxonomic_ranks ADD COLUMN raw_entry TEXT;
ALTER TABLE taxonomic_ranks ADD COLUMN country_id INTEGER;
ALTER TABLE taxonomic_ranks ADD COLUMN formation_id INTEGER;
ALTER TABLE taxonomic_ranks ADD COLUMN family TEXT;
```

### Step 3: taxa 데이터 마이그레이션

```sql
INSERT INTO taxonomic_ranks (
    name, rank, parent_id, author, year, year_suffix,
    type_species, type_species_author, formation, location,
    temporal_code, is_valid, notes, raw_entry,
    country_id, formation_id, family, created_at
)
SELECT
    t.name, 'Genus', t.family_id, t.author, t.year, t.year_suffix,
    t.type_species, t.type_species_author, t.formation, t.location,
    t.temporal_code, t.is_valid, t.notes, t.raw_entry,
    t.country_id, t.formation_id, t.family, t.created_at
FROM taxa t;
```

### Step 4: synonyms 테이블 업데이트

taxa.id → 새 taxonomic_ranks.id 매핑 적용:

```sql
-- 임시 매핑 테이블 생성
CREATE TEMP TABLE taxa_id_mapping AS
SELECT t.id as old_id, tr.id as new_id
FROM taxa t
JOIN taxonomic_ranks tr ON t.name = tr.name AND tr.rank = 'Genus';

-- junior_taxon_id, senior_taxon_id 업데이트
UPDATE synonyms SET junior_taxon_id = (
    SELECT new_id FROM taxa_id_mapping WHERE old_id = synonyms.junior_taxon_id
);
UPDATE synonyms SET senior_taxon_id = (
    SELECT new_id FROM taxa_id_mapping WHERE old_id = synonyms.senior_taxon_id
);
```

### Step 5: taxa 테이블 삭제

```sql
DROP INDEX idx_taxa_name;
DROP INDEX idx_taxa_family;
DROP INDEX idx_taxa_temporal;
DROP INDEX idx_taxa_country;
DROP INDEX idx_taxa_formation_id;
DROP TABLE taxa;
```

### Step 6: 인덱스 재생성

```sql
CREATE INDEX idx_taxonomic_ranks_name ON taxonomic_ranks(name);
CREATE INDEX idx_taxonomic_ranks_rank ON taxonomic_ranks(rank);
CREATE INDEX idx_taxonomic_ranks_parent ON taxonomic_ranks(parent_id);
CREATE INDEX idx_taxonomic_ranks_temporal ON taxonomic_ranks(temporal_code);
CREATE INDEX idx_taxonomic_ranks_country ON taxonomic_ranks(country_id);
CREATE INDEX idx_taxonomic_ranks_formation ON taxonomic_ranks(formation_id);
CREATE INDEX idx_taxonomic_ranks_valid ON taxonomic_ranks(is_valid);
```

### Step 7: 검증

- 총 레코드: 5,338개 (기존 225 + genus 5,113)
- synonyms 참조 무결성: 오류 0건
- 계층 구조 쿼리: 정상 동작

### Step 8: 하위 호환성 뷰 생성

```sql
CREATE VIEW taxa AS
SELECT
    id, name, rank, parent_id as family_id, author, year, year_suffix,
    type_species, type_species_author, formation, location, family,
    temporal_code, is_valid, notes, raw_entry, created_at,
    country_id, formation_id
FROM taxonomic_ranks
WHERE rank = 'Genus';
```

## 결과

### 테이블 변경

| 항목 | 이전 | 이후 |
|------|------|------|
| taxa 테이블 | 5,113 records | 삭제됨 (뷰로 대체) |
| taxonomic_ranks | 225 records | 5,338 records |

### taxonomic_ranks 구성

| Rank | 개수 |
|------|------|
| Class | 1 |
| Order | 12 |
| Suborder | 8 |
| Superfamily | 13 |
| Family | 191 |
| Genus | 5,113 |
| **총계** | **5,338** |

### Genus 통계

| 항목 | 값 |
|------|-----|
| 유효 Genus | 4,258 |
| 무효 Genus | 855 |

### 최종 테이블 목록

| 테이블/뷰 | 레코드 수 | 설명 |
|-----------|----------|------|
| taxonomic_ranks | 5,338 | 통합 분류 체계 (Class~Genus) |
| synonyms | 1,055 | 동의어 관계 |
| formations | 2,009 | 지층 정보 |
| countries | 151 | 국가 정보 |
| temporal_ranges | 28 | 지질시대 코드 |
| taxa (뷰) | 5,113 | 하위 호환성 뷰 |

### 최종 스키마

```sql
taxonomic_ranks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    rank TEXT NOT NULL,  -- Class, Order, Suborder, Superfamily, Family, Genus
    parent_id INTEGER,   -- FK → taxonomic_ranks.id (self-referential)
    author TEXT,
    year TEXT,
    year_suffix TEXT,
    genera_count INTEGER DEFAULT 0,
    taxa_count INTEGER DEFAULT 0,
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
```

## 샘플 쿼리

### 계층 구조 조회
```sql
SELECT
    g.name as genus,
    f.name as family,
    sf.name as superfamily,
    o.name as 'order'
FROM taxonomic_ranks g
LEFT JOIN taxonomic_ranks f ON g.parent_id = f.id
LEFT JOIN taxonomic_ranks sf ON f.parent_id = sf.id
LEFT JOIN taxonomic_ranks o ON sf.parent_id = o.id
WHERE g.rank = 'Genus' AND g.is_valid = 1
LIMIT 10;
```

### 하위 호환성 (taxa 뷰)
```sql
-- 기존 쿼리 그대로 사용 가능
SELECT * FROM taxa WHERE is_valid = 1 LIMIT 10;
```

## 백업 파일

- `trilobase_backup_phase9.db` - 작업 전 백업 (롤백용)
