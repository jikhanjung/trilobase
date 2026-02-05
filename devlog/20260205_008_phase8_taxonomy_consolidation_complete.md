# Phase 8: Taxonomy Table Consolidation 완료

**날짜:** 2026-02-05

## 목표

`taxonomic_ranks`, `families`, `taxa` 테이블의 분류 체계를 통합하여 일관된 계층 구조로 정리

## 작업 수행 내역

### Step 1: 데이터베이스 백업
```bash
cp trilobase.db trilobase_backup_20260205.db
```

### Step 2: taxonomic_ranks 컬럼 확장
```sql
ALTER TABLE taxonomic_ranks ADD COLUMN genera_count INTEGER DEFAULT 0;
ALTER TABLE taxonomic_ranks ADD COLUMN taxa_count INTEGER DEFAULT 0;
ALTER TABLE taxonomic_ranks ADD COLUMN year TEXT;
```

### Step 3: taxonomic_ranks 데이터 오류 수정

5개 Family의 이름에 author가 포함된 오류 수정:

| ID | 수정 전 | 수정 후 | Author |
|----|---------|---------|--------|
| 66 | Leiostegiidae Bradley, | Leiostegiidae | Bradley, 1925 |
| 87 | Cheiruridae Hawle & | Cheiruridae | Hawle & Corda, 1847 |
| 103 | Brachymetopidae Prantl and | Brachymetopidae | Prantl & Přibyl, 1951 |
| 141 | Remopleurididae Hawle and | Remopleurididae | Hawle & Corda, 1847 |
| 143 | Harpetidae Hawle & | Harpetidae | Hawle & Corda, 1847 |

### Step 4: 누락된 Family 추가

families 테이블에만 있던 22개 Family를 taxonomic_ranks에 추가:

```
Agnostidae, Ammagnostidae, Bohemillidae, Burlingiidae, Chengkouaspidae,
Clavagnostidae, Condylopygidae, Conokephalinidae, Diplagnostidae,
Dokimocephalidae, Doryagnostidae, Glyptagnostidae, Metagnostidae,
Ordosiidae, Pagodiidae, Peronopsidae, Pilekiidae, Ptychagnostidae,
Saukiidae, Toernquistiidae, Linguaproetidae, Scutelluidae
```

### Step 5: families 데이터 마이그레이션

```sql
UPDATE taxonomic_ranks
SET genera_count = (SELECT genera_count FROM families WHERE UPPER(families.name) = UPPER(taxonomic_ranks.name)),
    taxa_count = (SELECT taxa_count FROM families WHERE UPPER(families.name) = UPPER(taxonomic_ranks.name))
WHERE rank = 'Family';
```

### Step 6: taxa.family_id 업데이트

```sql
UPDATE taxa
SET family_id = (
    SELECT tr.id FROM taxonomic_ranks tr
    WHERE tr.rank = 'Family'
    AND UPPER(tr.name) = taxa.family
)
WHERE family IS NOT NULL AND family NOT IN ('INDET', 'UNCERTAIN', 'NEKTASPIDA');
```

### Step 7: 특수 케이스 처리

INDET, UNCERTAIN, NEKTASPIDA를 taxonomic_ranks에 추가하고 taxa와 연결:

```sql
INSERT INTO taxonomic_ranks (name, rank, notes) VALUES
  ('INDET', 'Family', '미확정 (Indeterminate)'),
  ('UNCERTAIN', 'Family', '불확실 (Uncertain placement)'),
  ('NEKTASPIDA', 'Family', 'Nektaspida - 비삼엽충 절지동물');

UPDATE taxa
SET family_id = (SELECT id FROM taxonomic_ranks WHERE name = taxa.family AND rank = 'Family')
WHERE family IN ('INDET', 'UNCERTAIN', 'NEKTASPIDA');
```

### Step 8: 검증

- 참조 무결성 검사: 0개 오류
- family_id 연결 완료: 4,771건
- family_id NULL: 342건 (family 필드 자체가 NULL인 무효 taxa)

### Step 9: families 테이블 삭제

```sql
DROP TABLE families;
```

### Step 10: 최종 검증

조인 쿼리 및 계층 구조 쿼리 정상 동작 확인

## 결과

### 테이블 변경

| 항목 | 이전 | 이후 |
|------|------|------|
| families 테이블 | 181 records | 삭제됨 |
| taxonomic_ranks | 200 records | 225 records |

### taxonomic_ranks 구성

| Rank | 개수 |
|------|------|
| Class | 1 |
| Order | 12 |
| Suborder | 8 |
| Superfamily | 13 |
| Family | 191 |
| **총계** | **225** |

### taxa.family_id 연결

| 항목 | 이전 | 이후 |
|------|------|------|
| 연결됨 | 4,660 (91.1%) | 4,771 (93.3%) |
| NULL | 453 | 342 |

### 스키마 변경

**taxonomic_ranks 테이블 (최종)**
```sql
taxonomic_ranks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    rank TEXT NOT NULL,  -- Class, Order, Suborder, Superfamily, Family
    parent_id INTEGER,   -- FK → taxonomic_ranks.id (self-referential)
    author TEXT,
    year TEXT,           -- 추가됨
    genera_count INTEGER DEFAULT 0,  -- 추가됨
    taxa_count INTEGER DEFAULT 0,    -- 추가됨
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES taxonomic_ranks(id)
)
```

## 샘플 쿼리

### taxa와 Family 조인
```sql
SELECT t.name as genus, tr.name as family, tr.genera_count, tr.taxa_count
FROM taxa t
JOIN taxonomic_ranks tr ON t.family_id = tr.id
WHERE tr.rank = 'Family'
LIMIT 10;
```

### 계층 구조 조회
```sql
SELECT
    f.name as family,
    sf.name as superfamily,
    o.name as 'order'
FROM taxonomic_ranks f
LEFT JOIN taxonomic_ranks sf ON f.parent_id = sf.id
LEFT JOIN taxonomic_ranks so ON sf.parent_id = so.id
LEFT JOIN taxonomic_ranks o ON so.parent_id = o.id
WHERE f.rank = 'Family' AND f.parent_id IS NOT NULL
LIMIT 10;
```

## 백업 파일

- `trilobase_backup_20260205.db` - 작업 전 백업 (롤백용)
