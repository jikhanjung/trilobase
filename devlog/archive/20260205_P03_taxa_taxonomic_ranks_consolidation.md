# Phase 9: Taxa와 Taxonomic_ranks 통합 계획

**날짜:** 2026-02-05

## 목표

`taxa`와 `taxonomic_ranks` 테이블을 통합하여 Class → Order → Suborder → Superfamily → Family → Genus 전체 계층을 단일 테이블로 관리

## 현재 상태

### taxa 테이블 (5,113 records)
```sql
taxa (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    rank TEXT DEFAULT 'genus',
    author TEXT,
    year INTEGER,
    year_suffix TEXT,
    type_species TEXT,
    type_species_author TEXT,
    formation TEXT,
    location TEXT,
    family TEXT,
    temporal_code TEXT,
    is_valid INTEGER DEFAULT 1,
    notes TEXT,
    raw_entry TEXT,
    created_at TEXT,
    country_id INTEGER,
    formation_id INTEGER,
    family_id INTEGER
)
```

### taxonomic_ranks 테이블 (225 records)
```sql
taxonomic_ranks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    rank TEXT NOT NULL,
    parent_id INTEGER,
    author TEXT,
    year TEXT,
    genera_count INTEGER DEFAULT 0,
    taxa_count INTEGER DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP
)
```

### 필드 비교

| 필드 | taxa | taxonomic_ranks | 통합 방안 |
|------|------|-----------------|-----------|
| id | ✓ | ✓ | 유지 |
| name | ✓ | ✓ | 유지 |
| rank | ✓ (genus) | ✓ | 유지 |
| author | ✓ | ✓ | 유지 |
| year | INTEGER | TEXT | INTEGER로 통일 |
| year_suffix | ✓ | - | 추가 |
| parent_id | - (family_id) | ✓ | 유지 (genus는 family_id → parent_id) |
| type_species | ✓ | - | 추가 (genus 전용) |
| type_species_author | ✓ | - | 추가 (genus 전용) |
| formation | ✓ | - | 추가 (genus 전용) |
| location | ✓ | - | 추가 (genus 전용) |
| temporal_code | ✓ | - | 추가 (genus 전용) |
| is_valid | ✓ | - | 추가 |
| raw_entry | ✓ | - | 추가 (genus 전용) |
| country_id | ✓ | - | 추가 (genus 전용) |
| formation_id | ✓ | - | 추가 (genus 전용) |
| genera_count | - | ✓ | 유지 (Family 이상) |
| taxa_count | - | ✓ | 유지 (Family 이상) |

## 통합 방안

### 통합 테이블 구조

```sql
taxonomic_ranks (
    -- 기본 필드 (모든 rank)
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    rank TEXT NOT NULL,  -- Class, Order, Suborder, Superfamily, Family, Genus
    parent_id INTEGER,
    author TEXT,
    year INTEGER,
    year_suffix TEXT,
    is_valid INTEGER DEFAULT 1,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 통계 필드 (Family 이상)
    genera_count INTEGER DEFAULT 0,
    taxa_count INTEGER DEFAULT 0,

    -- Genus 전용 필드
    type_species TEXT,
    type_species_author TEXT,
    formation TEXT,
    location TEXT,
    temporal_code TEXT,
    raw_entry TEXT,
    country_id INTEGER,
    formation_id INTEGER,

    FOREIGN KEY (parent_id) REFERENCES taxonomic_ranks(id),
    FOREIGN KEY (temporal_code) REFERENCES temporal_ranges(code),
    FOREIGN KEY (country_id) REFERENCES countries(id),
    FOREIGN KEY (formation_id) REFERENCES formations(id)
)
```

## 작업 순서

### Step 1: 데이터베이스 백업
```bash
cp trilobase.db trilobase_backup_phase9.db
```

### Step 2: taxonomic_ranks 테이블 확장

```sql
-- Genus 전용 필드 추가
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

-- year 컬럼 타입 변경 (TEXT → INTEGER) - SQLite에서는 실제로 유연함
```

### Step 3: taxa 데이터를 taxonomic_ranks로 마이그레이션

```sql
INSERT INTO taxonomic_ranks (
    name, rank, parent_id, author, year, year_suffix,
    type_species, type_species_author, formation, location,
    temporal_code, is_valid, notes, raw_entry,
    country_id, formation_id, created_at
)
SELECT
    t.name, 'Genus', t.family_id, t.author, t.year, t.year_suffix,
    t.type_species, t.type_species_author, t.formation, t.location,
    t.temporal_code, t.is_valid, t.notes, t.raw_entry,
    t.country_id, t.formation_id, t.created_at
FROM taxa t;
```

### Step 4: synonyms 테이블 업데이트

synonyms.junior_taxon_id와 senior_taxon_id가 새로운 taxonomic_ranks.id를 참조하도록 업데이트

```sql
-- 매핑 테이블 생성 (임시)
CREATE TEMP TABLE taxa_id_mapping AS
SELECT t.id as old_id, tr.id as new_id
FROM taxa t
JOIN taxonomic_ranks tr ON t.name = tr.name AND tr.rank = 'Genus';

-- synonyms 업데이트
UPDATE synonyms SET junior_taxon_id = (
    SELECT new_id FROM taxa_id_mapping WHERE old_id = junior_taxon_id
);
UPDATE synonyms SET senior_taxon_id = (
    SELECT new_id FROM taxa_id_mapping WHERE old_id = senior_taxon_id
);
```

### Step 5: taxa 테이블 삭제

```sql
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

1. 총 레코드 수 확인: 225 + 5,113 = 5,338
2. rank별 카운트 확인
3. synonyms 참조 무결성 확인
4. 계층 구조 쿼리 테스트

### Step 8: 뷰 생성 (하위 호환성)

```sql
-- 기존 taxa 테이블 형태의 뷰
CREATE VIEW taxa AS
SELECT
    id, name, rank, parent_id as family_id, author, year, year_suffix,
    type_species, type_species_author, formation, location,
    (SELECT name FROM taxonomic_ranks f WHERE f.id = taxonomic_ranks.parent_id) as family,
    temporal_code, is_valid, notes, raw_entry, created_at,
    country_id, formation_id
FROM taxonomic_ranks
WHERE rank = 'Genus';
```

## 예상 결과

### 통합 후 taxonomic_ranks

| Rank | 개수 |
|------|------|
| Class | 1 |
| Order | 12 |
| Suborder | 8 |
| Superfamily | 13 |
| Family | 191 |
| Genus | 5,113 |
| **총계** | **5,338** |

### 장점

1. 단일 테이블로 전체 분류 계층 관리
2. 재귀 쿼리로 계층 탐색 가능
3. 일관된 데이터 모델

### 단점

1. Genus 전용 필드가 상위 rank에서는 NULL
2. 테이블 크기 증가

## 롤백 계획

```bash
cp trilobase_backup_phase9.db trilobase.db
```

## 체크리스트

1. [ ] 데이터베이스 백업
2. [ ] taxonomic_ranks 컬럼 확장
3. [ ] taxa → taxonomic_ranks 마이그레이션
4. [ ] synonyms 테이블 업데이트
5. [ ] taxa 테이블 삭제
6. [ ] 인덱스 재생성
7. [ ] 검증
8. [ ] 뷰 생성 (선택)
9. [ ] HANDOVER.md 업데이트
10. [ ] 커밋
