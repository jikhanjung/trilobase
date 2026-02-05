# Phase 8: Taxonomy Table Consolidation

**날짜:** 2026-02-05

## 목표

`taxonomic_ranks`, `families`, `taxa` 테이블의 분류 체계를 통합하여 일관된 계층 구조로 정리

## 현재 상태 분석

### 테이블 현황

| 테이블 | 레코드 수 | 역할 |
|--------|----------|------|
| `taxonomic_ranks` | 200 | 계층적 분류 체계 (Class→Order→Suborder→Superfamily→Family) |
| `families` | 181 | Family 정보 (author, year, genera_count, taxa_count) |
| `taxa` | 5,113 | 속(genus) 정보, `family_id`로 families 참조 |

### taxonomic_ranks 구성

| Rank | 개수 |
|------|------|
| Class | 1 (Trilobita) |
| Order | 12 |
| Suborder | 8 |
| Superfamily | 13 |
| Family | 166 |

### 문제점

1. **중복 데이터**: `families`와 `taxonomic_ranks`에 Family 정보가 중복 저장
2. **불일치**:
   - `families`에만 있는 Family: 27개 (이름 정규화 차이)
   - `taxonomic_ranks`에만 있는 Family: 11개 (일부 author 포함 오류)
3. **참조 불일치**: `taxa.family_id`가 `families` 테이블을 참조하지만, 계층 구조는 `taxonomic_ranks`에 있음
4. **family_id NULL**: 453건
   - UNCERTAIN: 74건
   - INDET: 29건
   - NEKTASPIDA: 8건
   - family 자체가 NULL: 342건 (무효 taxa)

### 두 테이블 간 Family 불일치 상세

**families에만 있는 27개:**
```
Agnostidae, Ammagnostidae, Bohemillidae, Brachymetopidae, Burlingiidae,
Cheiruridae, Chengkouaspidae, Clavagnostidae, Condylopygidae, Conokephalinidae,
Diplagnostidae, Dokimocephalidae, Doryagnostidae, Glyptagnostidae, Harpetidae,
Leiostegiidae, Linguaproetidae, Metagnostidae, Ordosiidae, Pagodiidae,
Peronopsidae, Pilekiidae, Ptychagnostidae, Remopleurididae, Saukiidae,
Scutelluidae, Toernquistiidae
```

**taxonomic_ranks에만 있는 11개:**
```
Chengkouaspididae, Leiostegiidae Bradley,, Cheiruridae Hawle &,
Brachymetopidae Prantl and, Ehmaniellidae, Dokimokephalidae,
Loganellidae, Remopleurididae Hawle and, Harpetidae Hawle &,
Jamrogiidae, Onchonotopsidae
```

## 통합 계획

### 방안: taxonomic_ranks를 기본 테이블로 사용

**장점:**
- 이미 계층 구조(Class→Order→Suborder→Superfamily→Family) 구현됨
- self-referential 구조로 확장 가능
- Genus 레벨까지 확장 가능

### 단계별 작업

#### Step 1: taxonomic_ranks 테이블 확장

```sql
-- 추가 컬럼
ALTER TABLE taxonomic_ranks ADD COLUMN genera_count INTEGER DEFAULT 0;
ALTER TABLE taxonomic_ranks ADD COLUMN taxa_count INTEGER DEFAULT 0;
ALTER TABLE taxonomic_ranks ADD COLUMN year TEXT;
```

#### Step 2: taxonomic_ranks 데이터 정리

1. author 필드에 포함된 오류 수정 (예: "Leiostegiidae Bradley," → "Leiostegiidae")
2. families 테이블에만 있는 27개 Family를 taxonomic_ranks에 추가
3. 중복 Family 통합

#### Step 3: families 데이터 마이그레이션

```sql
-- families의 추가 정보를 taxonomic_ranks로 복사
UPDATE taxonomic_ranks
SET genera_count = (SELECT genera_count FROM families WHERE families.name = taxonomic_ranks.name),
    taxa_count = (SELECT taxa_count FROM families WHERE families.name = taxonomic_ranks.name),
    year = (SELECT year FROM families WHERE families.name = taxonomic_ranks.name)
WHERE rank = 'Family';
```

#### Step 4: taxa.family_id 업데이트

```sql
-- family_id를 taxonomic_ranks의 Family를 참조하도록 변경
UPDATE taxa
SET family_id = (
    SELECT tr.id FROM taxonomic_ranks tr
    WHERE tr.rank = 'Family'
    AND UPPER(tr.name) = taxa.family
)
WHERE family IS NOT NULL;
```

#### Step 5: 특수 케이스 처리

- UNCERTAIN, INDET, NEKTASPIDA는 별도 처리 (taxonomic_ranks에 추가하거나 NULL 유지)

#### Step 6: families 테이블 삭제

```sql
DROP TABLE families;
```

#### Step 7: 외래키 제약 조건 추가

```sql
-- taxa.family_id가 taxonomic_ranks.id를 참조하도록 설정
-- SQLite에서는 테이블 재생성 필요
```

## 예상 결과

### 통합 후 테이블 구조

```sql
taxonomic_ranks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    rank TEXT NOT NULL,  -- Class, Order, Suborder, Superfamily, Family
    parent_id INTEGER,   -- FK → taxonomic_ranks.id
    author TEXT,
    year TEXT,
    genera_count INTEGER DEFAULT 0,
    taxa_count INTEGER DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES taxonomic_ranks(id)
)

taxa (
    ...
    family_id INTEGER,   -- FK → taxonomic_ranks.id (rank='Family')
    ...
)
```

### 통합 후 예상 데이터

| 항목 | 개수 |
|------|------|
| taxonomic_ranks 총 레코드 | ~220 (기존 200 + 누락 Family ~20) |
| taxa.family_id 연결됨 | ~4,771 (기존 4,660 + 추가 111) |
| families 테이블 | 삭제됨 |

## 검증 항목

1. 모든 taxa.family_id가 taxonomic_ranks.id를 올바르게 참조
2. 계층 구조 무결성 (모든 Family가 상위 rank에 연결)
3. genera_count, taxa_count 정확성
4. 기존 쿼리 호환성

## 롤백 계획

작업 전 데이터베이스 백업:
```bash
cp trilobase.db trilobase_backup_20260205.db
```

## 작업 순서

1. [x] 데이터베이스 백업 → `trilobase_backup_20260205.db`
2. [x] taxonomic_ranks 테이블 확장 (genera_count, taxa_count, year 컬럼 추가)
3. [x] taxonomic_ranks 데이터 정리 (5개 Family 이름 오류 수정)
4. [x] 누락된 Family 추가 (22개)
5. [x] families 데이터 마이그레이션 (genera_count, taxa_count 복사)
6. [x] taxa.family_id 업데이트 (taxonomic_ranks 참조)
7. [x] 특수 케이스 처리 (INDET, UNCERTAIN, NEKTASPIDA 추가)
8. [x] 검증 완료
9. [x] families 테이블 삭제
10. [x] 최종 검증 완료

## 작업 결과

### 최종 통계

| 항목 | 값 |
|------|-----|
| taxonomic_ranks 총 레코드 | 225 |
| - Class | 1 |
| - Order | 12 |
| - Suborder | 8 |
| - Superfamily | 13 |
| - Family | 191 |
| taxa.family_id 연결됨 | 4,771 (93.3%) |
| taxa.family_id NULL | 342 (family 필드 없는 무효 taxa) |
| families 테이블 | 삭제됨 |

### 수정된 오류

1. `Leiostegiidae Bradley,` → `Leiostegiidae` (author: Bradley, 1925)
2. `Cheiruridae Hawle &` → `Cheiruridae` (author: Hawle & Corda, 1847)
3. `Brachymetopidae Prantl and` → `Brachymetopidae` (author: Prantl & Přibyl, 1951)
4. `Remopleurididae Hawle and` → `Remopleurididae` (author: Hawle & Corda, 1847)
5. `Harpetidae Hawle &` → `Harpetidae` (author: Hawle & Corda, 1847)

### 추가된 특수 케이스

| 이름 | 용도 | taxa 수 |
|------|------|---------|
| INDET | 미확정 | 29 |
| UNCERTAIN | 불확실 | 74 |
| NEKTASPIDA | 비삼엽충 절지동물 | 8 |
