# Phase 10: Formation/Location Relation 테이블 계획

**날짜:** 2026-02-05

## 목표

`formation`, `location` 필드를 synonym처럼 별도의 relation 테이블로 분리하여 다대다 관계 지원

## 현재 상태

### 데이터 현황

| 항목 | 값 |
|------|-----|
| Genus with formation | 4,854 |
| Genus with location | 4,847 |
| 고유 formation | 2,009 |
| 고유 location | 615 |

### 현재 스키마

```sql
-- taxonomic_ranks에 텍스트로 저장
taxonomic_ranks (
    ...
    formation TEXT,      -- 원본 텍스트 (예: "Blue Fjiord Fm")
    location TEXT,       -- 원본 텍스트 (예: "Nunavut, Canada")
    formation_id INTEGER, -- formations.id 참조
    country_id INTEGER,   -- countries.id 참조
    ...
)

-- 기존 참조 테이블
formations (id, name, normalized_name, formation_type, country, region, period, taxa_count)
countries (id, name, code, taxa_count)
```

### 문제점

1. 현재는 1:1 관계만 지원 (하나의 genus에 하나의 formation/location)
2. 실제로 하나의 genus가 여러 formation/location에서 발견될 수 있음
3. 다대다 관계를 위한 relation 테이블 필요

## 설계

### 새 테이블 구조

```sql
-- genus_formations: Genus와 Formation 간 다대다 관계
CREATE TABLE genus_formations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    genus_id INTEGER NOT NULL,      -- FK → taxonomic_ranks.id (rank='Genus')
    formation_id INTEGER NOT NULL,  -- FK → formations.id
    is_type_locality INTEGER DEFAULT 0,  -- 모식산지 여부
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (genus_id) REFERENCES taxonomic_ranks(id),
    FOREIGN KEY (formation_id) REFERENCES formations(id),
    UNIQUE(genus_id, formation_id)
);

-- genus_locations: Genus와 Location(Country) 간 다대다 관계
CREATE TABLE genus_locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    genus_id INTEGER NOT NULL,      -- FK → taxonomic_ranks.id (rank='Genus')
    country_id INTEGER NOT NULL,    -- FK → countries.id
    region TEXT,                    -- 세부 지역 (예: "Nunavut", "N Sichuan")
    is_type_locality INTEGER DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (genus_id) REFERENCES taxonomic_ranks(id),
    FOREIGN KEY (country_id) REFERENCES countries(id),
    UNIQUE(genus_id, country_id, region)
);
```

### 데이터 보존 원칙

- `taxonomic_ranks.formation`, `taxonomic_ranks.location` 원본 텍스트 필드는 **유지**
- `taxonomic_ranks.formation_id`, `taxonomic_ranks.country_id` 기존 참조도 **유지**
- 새 relation 테이블은 **추가**로 생성 (기존 데이터 손상 없음)

## 작업 순서

### Step 1: 데이터베이스 백업
```bash
cp trilobase.db trilobase_backup_phase10.db
```

### Step 2: Relation 테이블 생성

```sql
CREATE TABLE genus_formations (...);
CREATE TABLE genus_locations (...);
```

### Step 3: 기존 데이터 마이그레이션

```sql
-- genus_formations 채우기
INSERT INTO genus_formations (genus_id, formation_id)
SELECT tr.id, tr.formation_id
FROM taxonomic_ranks tr
WHERE tr.rank = 'Genus' AND tr.formation_id IS NOT NULL;

-- genus_locations 채우기
INSERT INTO genus_locations (genus_id, country_id, region)
SELECT tr.id, tr.country_id,
       CASE
           WHEN INSTR(tr.location, ',') > 0
           THEN TRIM(SUBSTR(tr.location, 1, INSTR(tr.location, ',') - 1))
           ELSE NULL
       END as region
FROM taxonomic_ranks tr
WHERE tr.rank = 'Genus' AND tr.country_id IS NOT NULL;
```

### Step 4: 인덱스 생성

```sql
CREATE INDEX idx_genus_formations_genus ON genus_formations(genus_id);
CREATE INDEX idx_genus_formations_formation ON genus_formations(formation_id);
CREATE INDEX idx_genus_locations_genus ON genus_locations(genus_id);
CREATE INDEX idx_genus_locations_country ON genus_locations(country_id);
```

### Step 5: 검증

1. genus_formations 레코드 수 확인 (예상: ~4,854)
2. genus_locations 레코드 수 확인 (예상: ~4,841)
3. 참조 무결성 검사

## 예상 결과

### 테이블 변경

| 테이블 | 이전 | 이후 |
|--------|------|------|
| genus_formations | - | ~4,854 records |
| genus_locations | - | ~4,841 records |
| taxonomic_ranks | 변경 없음 (원본 필드 유지) |

### 장점

1. 다대다 관계 지원 (향후 데이터 확장 가능)
2. 원본 데이터 보존
3. synonym 테이블과 일관된 패턴

## 샘플 쿼리

### 특정 Genus의 모든 Formation 조회
```sql
SELECT g.name as genus, f.name as formation
FROM taxonomic_ranks g
JOIN genus_formations gf ON g.id = gf.genus_id
JOIN formations f ON gf.formation_id = f.id
WHERE g.name = 'Paradoxides';
```

### 특정 Formation의 모든 Genus 조회
```sql
SELECT g.name as genus, g.author, g.year
FROM taxonomic_ranks g
JOIN genus_formations gf ON g.id = gf.genus_id
JOIN formations f ON gf.formation_id = f.id
WHERE f.name = 'Burgess Shale';
```

## 체크리스트

1. [ ] 데이터베이스 백업
2. [ ] genus_formations 테이블 생성
3. [ ] genus_locations 테이블 생성
4. [ ] 기존 데이터 마이그레이션
5. [ ] 인덱스 생성
6. [ ] 검증
7. [ ] HANDOVER.md 업데이트
8. [ ] 커밋
